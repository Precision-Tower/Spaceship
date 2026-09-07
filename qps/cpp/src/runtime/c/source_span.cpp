#include "../h/source_span.hpp"

#include <algorithm>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace qps {
namespace runtime {

namespace fs = std::filesystem;

std::vector<SourceSpan> normalizeSourceSpans(
    std::vector<SourceSpan> spans) {

    for (auto& span : spans) {
        if (span.start_line == 0 || span.end_line == 0) {
            throw std::runtime_error(
                "Source span lines are one-based.");
        }

        if (span.end_line < span.start_line) {
            throw std::runtime_error(
                "Source span end precedes start.");
        }

        span.path =
            fs::absolute(span.path)
                .lexically_normal();
    }

    std::sort(
        spans.begin(),
        spans.end(),
        [](const SourceSpan& left, const SourceSpan& right) {
            if (left.path != right.path) {
                return left.path.generic_string() <
                       right.path.generic_string();
            }

            if (left.start_line != right.start_line) {
                return left.start_line < right.start_line;
            }

            return left.end_line < right.end_line;
        });

    std::vector<SourceSpan> normalized;

    for (const auto& span : spans) {
        if (normalized.empty() ||
            normalized.back().path != span.path ||
            span.start_line > normalized.back().end_line + 1) {

            normalized.push_back(span);
            continue;
        }

        normalized.back().end_line =
            std::max(
                normalized.back().end_line,
                span.end_line);
    }

    return normalized;
}

std::string renderSourceSpans(
    const fs::path& workspace_root,
    const std::vector<SourceSpan>& input) {

    const auto spans =
        normalizeSourceSpans(input);

    const fs::path root =
        fs::absolute(workspace_root)
            .lexically_normal();

    std::ostringstream out;
    bool first_span = true;

    for (const auto& span : spans) {
        std::ifstream input_file(span.path);

        if (!input_file) {
            throw std::runtime_error(
                "Unable to open source span: " +
                span.path.string());
        }

        std::vector<std::string> lines;
        std::string line;

        while (std::getline(input_file, line)) {
            lines.push_back(line);
        }

        if (span.end_line > lines.size()) {
            throw std::runtime_error(
                "Source span exceeds file length: " +
                span.path.string());
        }

        if (!first_span) {
            out << "\n";
        }

        first_span = false;

        std::error_code error;
        fs::path shown =
            fs::relative(
                span.path,
                root,
                error);

        if (error ||
            shown.empty() ||
            shown.generic_string().rfind("..", 0) == 0) {

            shown = span.path;
        }

        out << shown.generic_string()
            << ":"
            << span.start_line;

        if (span.end_line != span.start_line) {
            out << "-" << span.end_line;
        }

        out << "\n";

        for (std::size_t number = span.start_line;
             number <= span.end_line;
             ++number) {

            out
                << number
                << ": "
                << lines[number - 1]
                << "\n";
        }
    }

    return out.str();
}

} // namespace runtime
} // namespace qps
