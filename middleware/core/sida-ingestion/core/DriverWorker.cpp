#include "DriverWorker.h"
#include <iostream>

namespace sida {

DriverWorker::DriverWorker(std::unique_ptr<IProtocolDriver> driver, 
                           uint32_t poll_rate_ms, 
                           ThreadSafeQueue<std::vector<TagRecord>>& queue)
    : driver_(std::move(driver)), 
      poll_rate_ms_(std::chrono::milliseconds(poll_rate_ms)), 
      output_queue_(queue), 
      running_(false)
{}

DriverWorker::~DriverWorker() {
    stop();
}

void DriverWorker::start() {
    if (!running_.exchange(true)) {
        std::cout << "[WORKER] Starting DriverWorker..." << std::endl;
        worker_thread_ = std::thread(&DriverWorker::pollingLoop, this);
    }
}

void DriverWorker::stop() {
    if (running_.exchange(false)) {
        std::cout << "[WORKER] Stopping DriverWorker..." << std::endl;
        if (worker_thread_.joinable()) {
            worker_thread_.join();
        }
    }
}

void DriverWorker::pollingLoop() {
    bool was_connected = false;

    while (running_) {
        auto start_time = std::chrono::steady_clock::now();

        if (!driver_->isConnected()) {
            
            if (was_connected) {
                std::cerr << "[WORKER] ALERTA: Conexão perdida! Disparando evento offline." << std::endl;
                
                std::vector<TagRecord> system_records;
                TagRecord death_record = TagRecord(driver_->getId(), "@status", 0.0, "", false);
                
                system_records.push_back(death_record);
                output_queue_.push(std::move(system_records));
                
                was_connected = false;
            }

            std::cout << "[WORKER] Driver not connected. Attempting to connect..." << std::endl;
            if (!driver_->connect()) {
                std::cout << "[WORKER] Connection failed. Retrying in " << poll_rate_ms_.count() << " ms." << std::endl;
                std::this_thread::sleep_for(poll_rate_ms_);
                continue;
            }
            
            std::cout << "[WORKER] Connected to driver." << std::endl;
            was_connected = true;
        }

        auto records = driver_->pollData();
        if (!records.empty()) {
            output_queue_.push(std::move(records));
        }

        auto end_time = std::chrono::steady_clock::now();
        auto elapsed_time = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        
        if (elapsed_time < poll_rate_ms_) {
            std::this_thread::sleep_for(poll_rate_ms_ - elapsed_time);
        } else {
            std::cerr << "[WORKER] Polling took longer than the specified poll rate of " 
                      << poll_rate_ms_.count() << " ms." << std::endl;
        }
    }
    
    driver_->disconnect();
}

} // namespace sida