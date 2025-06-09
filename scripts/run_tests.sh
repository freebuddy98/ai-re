#!/bin/bash

# AI-RE 项目测试运行脚本
# 支持单元测试、集成测试、端到端测试、验收测试的分别运行

set -e

# 默认配置
UNIT_ONLY=false
INTEGRATION_ONLY=false
E2E_ONLY=false
ACCEPTANCE_ONLY=false
VERBOSE=false
COVERAGE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            UNIT_ONLY=true
            shift
            ;;
        --integration)
            INTEGRATION_ONLY=true
            shift
            ;;
        --e2e)
            E2E_ONLY=true
            shift
            ;;
        --acceptance)
            ACCEPTANCE_ONLY=true
            shift
            ;;
        --all)
            # 运行所有测试（默认行为）
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help|-h)
            echo "使用方法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --unit         仅运行单元测试"
            echo "  --integration  仅运行集成测试"
            echo "  --e2e          仅运行端到端测试"
            echo "  --acceptance   仅运行验收测试（容器化测试）"
            echo "  --all          运行所有测试（默认）"
            echo "  --verbose,-v   详细输出"
            echo "  --coverage     生成覆盖率报告"
            echo "  --help,-h      显示此帮助信息"
            echo ""
            echo "说明:"
            echo "  验收测试需要Docker环境，会自动启动和停止容器"
            echo "  如需跳过特定测试，可设置环境变量："
            echo "    SKIP_INTEGRATION_TESTS=true  跳过集成测试"
            echo "    SKIP_E2E_TESTS=true          跳过端到端测试"
            echo "    SKIP_ACCEPTANCE_TESTS=true   跳过验收测试"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看帮助信息"
            exit 1
            ;;
    esac
done

# 设置测试参数
PYTEST_ARGS=""
if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS -v -s"
fi

if [[ "$COVERAGE" == "true" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=event_bus_framework --cov=input_service --cov-report=html --cov-report=term"
fi

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：运行单元测试
run_unit_tests() {
    log_info "开始运行单元测试..."
    
    # 运行 event_bus_framework 单元测试
    log_info "运行 event_bus_framework 单元测试..."
    cd libs/event_bus_framework
    python -m pytest tests/unit/ $PYTEST_ARGS -m "not slow"
    cd ../..
    log_success "event_bus_framework 单元测试完成"
    
    # 运行 input-service 单元测试  
    log_info "运行 input-service 单元测试..."
    cd services/input-service
    python -m pytest tests/unit/ $PYTEST_ARGS -m "not slow"
    cd ../..
    log_success "input-service 单元测试完成"
    
    log_success "所有单元测试完成"
}

# 函数：运行集成测试
run_integration_tests() {
    log_info "开始运行集成测试..."
    
    # 检查环境变量
    if [[ "${SKIP_INTEGRATION_TESTS}" == "true" ]]; then
        log_warning "跳过集成测试 (SKIP_INTEGRATION_TESTS=true)"
        return 0
    fi
    
    # 运行集成测试
    log_info "运行集成测试..."
    python -m pytest tests/integration/ $PYTEST_ARGS
    log_success "集成测试完成"
}

# 函数：运行端到端测试
run_e2e_tests() {
    log_info "开始运行端到端测试..."
    
    # 检查环境变量
    if [[ "${SKIP_E2E_TESTS}" == "true" ]]; then
        log_warning "跳过端到端测试 (SKIP_E2E_TESTS=true)"
        return 0
    fi
    
    # 运行端到端测试
    log_info "运行端到端测试..."
    python -m pytest tests/e2e/ $PYTEST_ARGS -m "not slow"
    log_success "端到端测试完成"
}

# 函数：运行验收测试
run_acceptance_tests() {
    log_info "开始运行验收测试（容器化测试）..."
    
    # 检查环境变量
    if [[ "${SKIP_ACCEPTANCE_TESTS}" == "true" ]]; then
        log_warning "跳过验收测试 (SKIP_ACCEPTANCE_TESTS=true)"
        return 0
    fi
    
    # 检查Docker环境
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，跳过验收测试"
        return 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose不可用，跳过验收测试"
        return 1
    fi
    
    # 运行验收测试 - 使用专门的脚本
    if [[ "$VERBOSE" == "true" ]]; then
        export VERBOSE=true
    fi
    
    if ./scripts/run_container_acceptance_tests.sh --all; then
        log_success "验收测试完成"
        return 0
    else
        log_error "验收测试失败"
        return 1
    fi
}

# 主逻辑
if [[ "$UNIT_ONLY" == "true" ]]; then
    run_unit_tests
elif [[ "$INTEGRATION_ONLY" == "true" ]]; then
    run_integration_tests
elif [[ "$E2E_ONLY" == "true" ]]; then
    run_e2e_tests
elif [[ "$ACCEPTANCE_ONLY" == "true" ]]; then
    run_acceptance_tests
else
    # 运行所有测试
    log_info "开始运行完整测试套件..."
    
    run_unit_tests
    echo ""
    
    if [[ "${SKIP_INTEGRATION_TESTS}" != "true" ]]; then
        run_integration_tests
        echo ""
    else
        log_warning "跳过集成测试 (SKIP_INTEGRATION_TESTS=true)"
    fi
    
    if [[ "${SKIP_E2E_TESTS}" != "true" ]]; then
        run_e2e_tests
        echo ""
    else
        log_warning "跳过端到端测试 (SKIP_E2E_TESTS=true)"
    fi
    
    if [[ "${SKIP_ACCEPTANCE_TESTS}" != "true" ]]; then
        run_acceptance_tests
        echo ""
    else
        log_warning "跳过验收测试 (SKIP_ACCEPTANCE_TESTS=true)"
    fi
    
    log_success "完整测试套件运行完成"
fi

# 如果启用了覆盖率，显示报告位置
if [[ "$COVERAGE" == "true" ]]; then
    echo ""
    log_info "覆盖率报告已生成："
    echo "  HTML 报告: htmlcov/index.html"
    echo "  终端报告: 见上方输出"
fi 