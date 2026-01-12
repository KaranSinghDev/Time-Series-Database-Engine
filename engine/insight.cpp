#include "shard.h" // The only header it needs besides standard library ones
#include "insight.h" // And its own header for consistency
#include <string>
#include <vector>
#include <filesystem>

std::string get_shard_path(uint64_t timestamp); // Forward declaration

extern "C" {
    // The implementation of the ingest function, which delegates to the ShardWriter class.
    void ingest_point(uint64_t timestamp, double value) {
        std::string file_path = get_shard_path(timestamp);
        ShardWriter writer(file_path);
        writer.append({timestamp, value});
        writer.close();
    }

    // The implementation of the query function, which delegates to the ShardReader class.
    int64_t query_range(uint64_t start_ts, uint64_t end_ts, DataPoint* out_buffer, int64_t buffer_capacity) {
        int64_t points_found = 0;
        const uint64_t SHARD_DURATION_MS = 3600000;
        const std::string DATA_DIRECTORY = "data";

        uint64_t first_shard_start = (start_ts / SHARD_DURATION_MS) * SHARD_DURATION_MS;
        uint64_t last_shard_start = (end_ts / SHARD_DURATION_MS) * SHARD_DURATION_MS;

        for (uint64_t shard_start = first_shard_start; shard_start <= last_shard_start; shard_start += SHARD_DURATION_MS) {
            uint64_t shard_end = shard_start + SHARD_DURATION_MS - 1;
            std::string file_path = DATA_DIRECTORY + "/" + std::to_string(shard_start) + "-" + std::to_string(shard_end) + ".bin";
            
            if (!std::filesystem::exists(file_path)) continue;

            ShardReader reader(file_path);
            std::vector<DataPoint> points = reader.read_all();

            for (const auto& point : points) {
                if (points_found < buffer_capacity && point.timestamp >= start_ts && point.timestamp <= end_ts) {
                    out_buffer[points_found] = point;
                    points_found++;
                }
            }
        }
        return points_found;
    }
} 

// The implementation of the helper function.
std::string get_shard_path(uint64_t timestamp) {
    const uint64_t SHARD_DURATION_MS = 3600000;
    const std::string DATA_DIRECTORY = "data";
    uint64_t shard_start_ts = (timestamp / SHARD_DURATION_MS) * SHARD_DURATION_MS;
    uint64_t shard_end_ts = shard_start_ts + SHARD_DURATION_MS - 1;
    std::filesystem::create_directory(DATA_DIRECTORY);
    return DATA_DIRECTORY + "/" + std::to_string(shard_start_ts) + "-" + std::to_string(shard_end_ts) + ".bin";
}