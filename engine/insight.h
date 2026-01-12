#ifndef INSIGHT_H
#define INSIGHT_H

#include <cstdint>

// Forward-declare the DataPoint struct to avoid including the full shard.h here.
// This is a good practice for keeping header dependencies minimal.
struct DataPoint;

// Use 'extern "C"' to ensure these functions have C-style (unmangled) names,
// which is essential for our Python ctypes bridge to find them.
#ifdef __cplusplus
extern "C" {
#endif

void ingest_point(uint64_t timestamp, double value);

int64_t query_range(uint64_t start_ts, uint64_t end_ts, DataPoint* out_buffer, int64_t buffer_capacity);

#ifdef __cplusplus
}
#endif

#endif // INSIGHT_H