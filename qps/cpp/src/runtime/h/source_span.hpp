#ifndef QPS_RUNTIME_H_SOURCE_SPAN_HPP
#define QPS_RUNTIME_H_SOURCE_SPAN_HPP

#include <filesystem>
#include <string>
#include <vector>

namespace qps {
namespace runtime {

struct SourceSpan {
    std::filesystem::path path;
    std::size_t start_line = 1;
    std::size_t end_line = 1;
};

std::vector<SourceSpan> normalizeSourceSpans(
    std::vector<SourceSpan> spans);

std::string renderSourceSpans(
    const std::filesystem::path& workspace_root,
    const std::vector<SourceSpan>& spans);

} // namespace runtime
} // namespace qps

#endif
