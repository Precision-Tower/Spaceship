#include "../h/document_loader.hpp"

#include "../../ast/ast_node.hpp"
#include "../../parser/h/_index.hpp"
#include "../../tokens/h/char_stream.hpp"
#include "../../tokens/h/lexer.hpp"
#include "../../utils.hpp"

#include <string>

namespace qps {
namespace runtime {

std::unique_ptr<ast::ProgramNode> DocumentLoader::load(
    const std::filesystem::path& file) const {

    const std::string source =
        utils::readFileContents(file.string());

    tokens::CharStream char_stream(source);
    tokens::Lexer lexer(char_stream);
    parser::Parser parser(lexer);

    return parser.parseProgram();
}

} // namespace runtime
} // namespace qps
