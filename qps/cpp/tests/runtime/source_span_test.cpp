#include "runtime/h/source_span.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

void require(
    bool condition,
    const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

int main() {
    const fs::path root =
        fs::temp_directory_path() /
        "qps_source_span_test";

    fs::remove_all(root);
    fs::create_directories(root);

    const fs::path source =
        root / "sample.txt";

    {
        std::ofstream out(source);
        out
            << "one\n"
            << "two\n"
            << "three\n"
            << "four\n"
            << "five\n"
            << "six\n";
    }

    const std::vector<qps::runtime::SourceSpan> spans{
        {source, 2, 4},
        {source, 3, 5},
        {source, 6, 6},
        {source, 2, 2}
    };

    const auto normalized =
        qps::runtime::normalizeSourceSpans(spans);

    require(
        normalized.size() == 1,
        "overlapping/adjacent spans were not merged");

    require(
        normalized[0].start_line == 2 &&
        normalized[0].end_line == 6,
        "normalized source range mismatch");

    const std::string rendered =
        qps::runtime::renderSourceSpans(
            root,
            spans);

    const std::string expected =
        "sample.txt:2-6\n"
        "2: two\n"
        "3: three\n"
        "4: four\n"
        "5: five\n"
        "6: six\n";

    require(
        rendered == expected,
        "source span rendering contract mismatch:\n" +
        rendered);

    fs::remove_all(root);

    std::cout
        << "QPS source span: PASS\n";

    return 0;
}
