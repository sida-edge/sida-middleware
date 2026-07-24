#include "core/DriverWorker.h"
#include "core/ThreadSafeQueue.h"
#include "core/ManifestParser.h"

#include "drivers/modbus/ModbusDriver.h"
#include "drivers/opcua/OpcUaDriver.h"

#include <zmq.hpp>
#include <nlohmann/json.hpp>
#include <curl/curl.h>

#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <thread>
#include <atomic>
#include <fstream>

using json = nlohmann::json;

const std::string MANIFEST_API_URL = "http://sida-core:1880/api/manifest";

std::atomic<bool> reload_manifest{true};
std::atomic<bool> system_running{true};

nlohmann::json VariantToJson(const TagValue& val) {
    return std::visit([](auto&& arg) -> nlohmann::json {
        return arg;
    }, val);
}

size_t CurlWriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    std::string* str = static_cast<std::string*>(userp);
    str->append(static_cast<char*>(contents), total_size);
    return total_size;
}

bool PerformHttpGet(const std::string& url, std::string& response_data) {
    CURL* curl = curl_easy_init();
    if (!curl) return false;

    // Limpa a string de resposta para evitar sujeira de requisições anteriores
    response_data.clear(); 

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, CurlWriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response_data);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 5L); // 5s timeout

    CURLcode res = curl_easy_perform(curl);
    curl_easy_cleanup(curl);

    if (res == CURLE_OK) {
        return true;
    } else {
        std::cerr << "[HTTP ERROR] Falha no GET para " << url << ": " << curl_easy_strerror(res) << "\n";
        return false;
    }
}

void ZmqConfigSubscriber() {
    zmq::context_t ctx(1);
    zmq::socket_t sub(ctx, zmq::socket_type::sub);
    
    try {
        sub.connect("tcp://sida-core:5556");
        sub.set(zmq::sockopt::subscribe, "sida/manifest");
        std::cout << "[CONFIG] Escutando atualizacoes no topico 'sida/manifest'...\n";
    } catch (...) {
        std::cerr << "[CONFIG] Erro ao conectar no canal de atualizacao.\n";
        return;
    }

    while (system_running) {
        zmq::message_t topic_msg;
        auto res = sub.recv(topic_msg, zmq::recv_flags::none); 
        if (res) {
            zmq::message_t payload_msg;
            auto res_payload = sub.recv(payload_msg, zmq::recv_flags::none);
            std::cout << "[CONFIG] Sinal de atualizacao recebido via ZMQ! Agendando recarregamento...\n";
            reload_manifest = true;
        }
        std::cout << "[CONFIG] Loop de escuta ativo. Aguardando atualizacoes...\n";
    }
}

int main() {
    std::cout << "[SIDA INGESTION] Starting Service..." << std::endl;

    curl_global_init(CURL_GLOBAL_DEFAULT);

    sida::ThreadSafeQueue<std::vector<sida::TagRecord>> data_queue;
    std::vector<std::unique_ptr<sida::DriverWorker>> workers;
    std::string gateway_id = "unknown";

    zmq::context_t zmq_context(1);
    zmq::socket_t zmq_push(zmq_context, zmq::socket_type::push);
    try {
        zmq_push.bind("tcp://*:5555");
    } catch (const std::exception& e) {
        std::cerr << "[ZMQ FATAL] Falha bind IPC: " << e.what() << "\n";
        return 1;
    }

    std::thread config_thread(ZmqConfigSubscriber);

    while (system_running) {
        if (reload_manifest) {
            std::cout << "[SIDA_INGESTION] Iniciando processo de Hot Reload...\n";
            
            for (auto& w : workers) {
                w->stop();
            }
            workers.clear(); 

            std::string info_url = "http://sida-core:8000/api/system/info";
            std::string info_response;
            
            if (PerformHttpGet(info_url, info_response)) {
                try {
                    json info_json = json::parse(info_response);
                    gateway_id = info_json.value("gateway_id", "sida_default_gw");
                    std::cout << "[SIDA_INGESTION] Identidade confirmada. Gateway ID: " << gateway_id << "\n";
                    
                    std::string manifest_url = "http://sida-core:8000/api/config/manifest?gateway_id=" + gateway_id;
                    std::string manifest_response;
                    
                    if (PerformHttpGet(manifest_url, manifest_response)) {
                        std::string temp_manifest = "/tmp/manifest.json";
                        std::ofstream outfile(temp_manifest);
                        outfile << manifest_response;
                        outfile.close();

                        sida::ManifestParser parser(temp_manifest);
                        std::vector<sida::DeviceConfig> devices = parser.parseEnabledDevices();

                        for (const auto& d_cfg : devices) {
                            if (d_cfg.protocol == "modbus_tcp") {
                                auto modbus_drv = std::make_unique<sida::ModbusDriver>(d_cfg);
                                workers.push_back(std::make_unique<sida::DriverWorker>(
                                    std::move(modbus_drv), d_cfg.scan_rate_ms, data_queue
                                ));
                            } else if (d_cfg.protocol == "opcua") {
                                auto opcua_drv = std::make_unique<sida::OpcUaDriver>(d_cfg);
                                workers.push_back(std::make_unique<sida::DriverWorker>(
                                    std::move(opcua_drv), d_cfg.scan_rate_ms, data_queue
                                ));
                            } else {
                                std::cerr << "[SIDA_INGESTION] Protocolo desconhecido para o dispositivo " << d_cfg.device_id << ": " << d_cfg.protocol << "\n";
                            }
                        }

                        for (auto& w : workers) {
                            w->start();
                        }
                        std::cout << "[SIDA_INGESTION] Hot Reload concluido. " << workers.size() << " workers ativos.\n";
                    
                    } else {
                        std::cerr << "[SIDA_INGESTION] Falha ao baixar manifesto. Sistema pausado.\n";
                    }

                } catch (const json::parse_error& e) {
                    std::cerr << "[ORQUESTRADOR] Erro ao decodificar /system/info: " << e.what() << "\n";
                }
            } else {
                std::cerr << "[SIDA_INGESTION] Falha ao obter identidade do gateway. Sistema pausado.\n";
            }

            std::cout << "[SIDA_INGESTION] Loop principal ativo. Workers: " << workers.size() << "\n";
            reload_manifest = false; 
        }

        std::vector<sida::TagRecord> data_batch;
        if (data_queue.popFor(data_batch, std::chrono::milliseconds(500))) {
            if (data_batch.empty()) continue;

            json payload;
            payload["timestamp"] = data_batch[0].timestamp;
            payload["gateway_id"] = gateway_id;
            
            payload["source"] = {
                {"device_id", data_batch[0].device_id},
                {"source_protocol", "modbus_tcp"}
            };

            json data_obj = json::object();
            for (const auto& tag : data_batch) {
                data_obj[tag.tag_name] = VariantToJson(tag.value);
            }
            
            payload["data"] = data_obj;
            std::string serialized = payload.dump();

            zmq::message_t msg(serialized.size());
            memcpy(msg.data(), serialized.data(), serialized.size());
            auto result = zmq_push.send(msg, zmq::send_flags::dontwait);

            if (!result) {
                std::cerr << "[SIDA_INGESTION] Consumidor offline ou buffer cheio. Descartando pacote para proteger a memoria!\n";
            }
        }
    }
    
    std::cout << "[SIDA_INGESTION] Sistema encerrando. Parando workers...\n";
    for (auto& w : workers) w->stop();
    curl_global_cleanup();
    system_running = false;
    config_thread.join();

    return 0;
}