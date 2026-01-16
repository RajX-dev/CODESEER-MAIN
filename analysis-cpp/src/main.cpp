#include <clang/AST/ASTConsumer.h>
#include <clang/AST/RecursiveASTVisitor.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendAction.h>
#include <clang/Tooling/CommonOptionsParser.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/raw_ostream.h>

using namespace clang;
using namespace clang::tooling;

class FunctionVisitor : public RecursiveASTVisitor<FunctionVisitor> {
public:
    bool VisitFunctionDecl(FunctionDecl* func) {
        if (func->hasBody()) {
            llvm::outs() << "Function: "
                         << func->getNameAsString()
                         << "\n";
        }
        return true;
    }
};

class ASTConsumerImpl : public ASTConsumer {
public:
    FunctionVisitor visitor;

    void HandleTranslationUnit(ASTContext& context) override {
        visitor.TraverseDecl(context.getTranslationUnitDecl());
    }
};

class FrontendActionImpl : public ASTFrontendAction {
public:
    std::unique_ptr<ASTConsumer> CreateASTConsumer(
        CompilerInstance&, llvm::StringRef) override {
        return std::make_unique<ASTConsumerImpl>();
    }
};

int main(int argc, const char** argv) {
    llvm::cl::OptionCategory ToolCategory("codeseer options");

    auto expectedParser =
        CommonOptionsParser::create(argc, argv, ToolCategory);

    if (!expectedParser) {
        llvm::errs() << "Failed to parse options\n";
        return 1;
    }

    CommonOptionsParser& optionsParser = expectedParser.get();
    ClangTool tool(optionsParser.getCompilations(),
                   optionsParser.getSourcePathList());

    return tool.run(newFrontendActionFactory<FrontendActionImpl>().get());
}
