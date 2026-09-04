// qps/core/utils.cpp

#include "utils.hpp"
#include <fstream>   // For file I/O
#include <sstream>   // For stringstream
#include <iostream>  // For console output

namespace qps {
namespace utils {

// Implements a utility to read the entire contents of a file into a string.
// This is useful for loading .qps source files into the CharStream.
std::string readFileContents(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        // We could throw an error or return an empty string/optional.
        // For now, throw to signal inability to read source.
        throw std::runtime_error("Could not open file: " + filepath);
    }
    std::stringstream buffer;
    buffer << file.rdbuf(); // Read entire file content into stringstream
    return buffer.str();
}

// Implements a simple logging function to print messages to the console.
// This can be expanded into a full-fledged logging system later.
void logMessage(const std::string& message) {
    std::cout << "[QPS_LOG] " << message << std::endl;
}

} // namespace utils
} // namespace qps
