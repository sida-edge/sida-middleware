#ifndef SIDA_INGESTION_CORE_THREADSAFEQUEUE
#define SIDA_INGESTION_CORE_THREADSAFEQUEUE

#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>

namespace sida {

template <typename T>
class ThreadSafeQueue {
  public:
    ThreadSafeQueue() = default;
    ~ThreadSafeQueue() { shutdown(); }

    void push(T item) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            queue_.push(std::move(item));
        }
        cond_var_.notify_one();
    }

    bool pop(T& item) {
        std::unique_lock<std::mutex> lock(mutex_);
        cond_var_.wait(lock, [this] { return !queue_.empty() || shutdown_.load(); });

        if (shutdown_.load() && queue_.empty()) {
            return false;
        }

        item = std::move(queue_.front());
        queue_.pop();
        return true;
    }

    bool popFor(T& item, std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> lock(mutex_);
        bool got_data = cond_var_.wait_for(lock, std::chrono::milliseconds(timeout), [this]() { 
            return !queue_.empty() || shutdown_.load(); 
        });
        
        if (shutdown_.load() && queue_.empty()) return false;
        if (!got_data || queue_.empty()) return false;
        
        item = std::move(queue_.front());
        queue_.pop();
        return true;
    }

    void shutdown() {
        shutdown_.store(true);
        cond_var_.notify_all();
    }

  private:
    std::queue<T> queue_;
    std::mutex mutex_;
    std::condition_variable cond_var_;
    std::atomic<bool> shutdown_{false};
};

} // namespace sida

#endif /* SIDA_INGESTION_CORE_THREADSAFEQUEUE */
