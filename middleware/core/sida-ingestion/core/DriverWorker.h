#ifndef SIDA_INGESTION_CORE_DRIVERWORKER
#define SIDA_INGESTION_CORE_DRIVERWORKER

#include "IProtocolDriver.h"
#include "ThreadSafeQueue.h"
#include <thread>
#include <memory>
#include <atomic>
#include <chrono>

namespace sida {

class DriverWorker {
  public:
    DriverWorker(std::unique_ptr<IProtocolDriver> driver, 
                 uint32_t poll_rate_ms, 
                 ThreadSafeQueue<std::vector<TagRecord>>& queue);

    ~DriverWorker();

    void start();
    void stop();

  private:
    std::unique_ptr<IProtocolDriver> driver_;
    std::chrono::milliseconds poll_rate_ms_;
    ThreadSafeQueue<std::vector<TagRecord>>& output_queue_;

    std::thread worker_thread_;
    std::atomic<bool> running_;

    void pollingLoop();
};

} // namespace sida

#endif /* SIDA_INGESTION_CORE_DRIVERWORKER */
