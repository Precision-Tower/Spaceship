// qps/core/utils.hpp

#ifndef QPS_UTILS_HPP
#define QPS_UTILS_HPP

#include <string>
#include <vector>

// This file provides general-purpose utility functions
// that are not specific to any one core module but are used across the engine.

namespace qps {
namespace utils {

// Example: Function to read an entire file into a string.
std::string readFileContents(const std::string& filepath);

// Example: Simple function to print a message to console (can be replaced by a logger later).
void logMessage(const std::string& message);

} // namespace utils
} // namespace qps

#endif // QPS_UTILS_HPP
