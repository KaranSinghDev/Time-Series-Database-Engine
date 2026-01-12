#include "shard.h"
#include "insight.h" // <<< THIS IS THE MISSING LINE
#include <gtest/gtest.h>
#include <filesystem>
#include <vector>
// ...

// --- Test Fixture for Sharded Queries ---
// A test fixture is a class that inherits from ::testing::Test.
// It allows us to reuse the same configuration and helper functions for multiple tests.
// GTest will automatically call SetUp() before each test and TearDown() after.
class ShardedQueryTest : public ::testing::Test {
protected:
    // This function runs BEFORE every TEST_F in this suite.
    void SetUp() override {
        cleanup_test_data();
        setup_test_data();
    }

    // This function runs AFTER every TEST_F in this suite.
    void TearDown() override {
        cleanup_test_data();
    }

    // Helper functions are defined here for clarity and reuse.
    void setup_test_data() {
        // Shard 0 (0 - 3,599,999 ms)
        ingest_point(1000, 10.0);
        ingest_point(2000, 20.0);

        // Shard 1 (3,600,000 - 7,199,999 ms)
        ingest_point(3600000, 30.0);
        ingest_point(4000000, 40.0);

        // Shard 2 (7,200,000 - 10,799,999 ms)
        ingest_point(8000000, 50.0);
    }

    void cleanup_test_data() {
        if (std::filesystem::exists(DATA_DIRECTORY)) {
            std::filesystem::remove_all(DATA_DIRECTORY);
        }
    }

    // Member variables available to all tests in this fixture.
    const int BUFFER_SIZE = 10;
    DataPoint results_buffer[10];
    const std::string DATA_DIRECTORY = "data";
};

// --- Test Cases ---
// We use TEST_F() to indicate that this test uses the 'ShardedQueryTest' Fixture.
// Each TEST_F is a separate, independent test case.

TEST_F(ShardedQueryTest, QueryWithinSingleShard) {
    int64_t count = query_range(0, 3000, results_buffer, BUFFER_SIZE);
    
    // ASSERT_EQ provides much better error messages than a manual assert().
    // It will print the expected and actual values on failure.
    ASSERT_EQ(count, 2);
    // EXPECT_EQ will report a failure but allow the test to continue.
    EXPECT_EQ(results_buffer[0].timestamp, 1000);
    EXPECT_EQ(results_buffer[0].value, 10.0);
    EXPECT_EQ(results_buffer[1].timestamp, 2000);
    EXPECT_EQ(results_buffer[1].value, 20.0);
}

TEST_F(ShardedQueryTest, QuerySpanningTwoShards) {
    int64_t count = query_range(1500, 3700000, results_buffer, BUFFER_SIZE);
    
    ASSERT_EQ(count, 2);
    EXPECT_EQ(results_buffer[0].timestamp, 2000);
    EXPECT_EQ(results_buffer[1].timestamp, 3600000);
}

TEST_F(ShardedQueryTest, QuerySpanningAllShards) {
    int64_t count = query_range(0, 9000000, results_buffer, BUFFER_SIZE);
    ASSERT_EQ(count, 5);
}

TEST_F(ShardedQueryTest, QueryWithNoResults) {
    int64_t count = query_range(12000000, 13000000, results_buffer, BUFFER_SIZE);
    ASSERT_EQ(count, 0);
}

TEST_F(ShardedQueryTest, QueryWithInsufficientBuffer) {
    // This tests that our function correctly handles a full buffer and doesn't write out of bounds.
    int64_t count = query_range(0, 9000000, results_buffer, 3); // Buffer only has space for 3 points
    ASSERT_EQ(count, 3);
}

// NOTE: We no longer need a main() function in this file.
// The GTest::gtest_main library that we link provides its own main().