#!/bin/bash

# 容器验收测试运行脚本 (Container Acceptance Test Runner)
# 运行容器化环境的验收测试，包括编排、性能、数据持久化等测试

set -e

# 配置变量
PROJECT_NAME="ai-re-acceptance-test"
COMPOSE_FILE="docker-compose.yml"
TEST_TIMEOUT=300  # 5分钟超时
VERBOSE=${VERBOSE:-false}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 显示帮助信息
show_help() {
    echo "容器验收测试运行脚本"
    echo ""
    echo "用法: $0 [OPTIONS]"
    echo ""
    echo "选项:"
    echo "  --orchestration    运行容器编排测试"
    echo "  --performance      运行容器性能测试"
    echo "  --persistence      运行数据持久化测试"
    echo "  --all             运行所有验收测试"
    echo "  --cleanup-only    仅清理测试环境"
    echo "  --verbose         详细输出"
    echo "  --help            显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --all              # 运行所有验收测试"
    echo "  $0 --orchestration    # 仅运行编排测试"
    echo "  $0 --cleanup-only     # 清理测试环境"
}

# 检查Docker环境
check_docker_environment() {
    log_info "检查Docker环境..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装或不在PATH中"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装或不可用"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon未运行或无权限访问"
        exit 1
    fi
    
    log_success "Docker环境检查通过"
}

# 检查依赖
check_dependencies() {
    log_info "检查测试依赖..."
    
    # 检查Python依赖
    if ! python -c "import docker, pytest, requests, redis" &> /dev/null; then
        log_warning "部分Python依赖缺失，尝试安装..."
        pip install docker pytest requests redis psutil
    fi
    
    log_success "依赖检查完成"
}

# 清理测试环境
cleanup_test_environment() {
    log_info "清理测试环境..."
    
    # 停止并删除容器
    docker compose -p "${PROJECT_NAME}" down -v --remove-orphans &> /dev/null || true
    docker compose -p "ai-re-perf-test" down -v --remove-orphans &> /dev/null || true
    docker compose -p "ai-re-persistence-test" down -v --remove-orphans &> /dev/null || true
    
    # 清理悬空镜像
    docker image prune -f &> /dev/null || true
    
    # 清理悬空卷
    docker volume prune -f &> /dev/null || true
    
    log_success "测试环境清理完成"
}

# 准备测试环境
setup_test_environment() {
    log_info "准备测试环境..."
    
    # 确保在项目根目录
    if [ ! -f "${COMPOSE_FILE}" ]; then
        log_error "未找到 ${COMPOSE_FILE}，请在项目根目录运行此脚本"
        exit 1
    fi
    
    # 构建镜像
    log_info "构建应用镜像..."
    docker compose -p "${PROJECT_NAME}" build --no-cache
    
    # 启动基础服务
    log_info "启动测试环境..."
    docker compose -p "${PROJECT_NAME}" up -d
    
    # 等待服务就绪
    log_info "等待服务就绪..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_success "服务已就绪"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    log_error "服务启动超时"
    docker compose -p "${PROJECT_NAME}" logs
    exit 1
}

# 运行容器编排测试
run_orchestration_tests() {
    log_info "运行容器编排验收测试..."
    
    local test_cmd="pytest tests/acceptance/test_container_orchestration.py -v"
    
    if [ "$VERBOSE" = true ]; then
        test_cmd="$test_cmd -s"
    fi
    
    if timeout "$TEST_TIMEOUT" $test_cmd; then
        log_success "容器编排测试通过"
        return 0
    else
        log_error "容器编排测试失败"
        return 1
    fi
}

# 运行容器性能测试
run_performance_tests() {
    log_info "运行容器性能验收测试..."
    
    local test_cmd="pytest tests/acceptance/test_container_performance.py -v"
    
    if [ "$VERBOSE" = true ]; then
        test_cmd="$test_cmd -s"
    fi
    
    if timeout "$TEST_TIMEOUT" $test_cmd; then
        log_success "容器性能测试通过"
        return 0
    else
        log_error "容器性能测试失败"
        return 1
    fi
}

# 运行数据持久化测试
run_persistence_tests() {
    log_info "运行数据持久化验收测试..."
    
    local test_cmd="pytest tests/acceptance/test_container_data_persistence.py -v"
    
    if [ "$VERBOSE" = true ]; then
        test_cmd="$test_cmd -s"
    fi
    
    if timeout "$TEST_TIMEOUT" $test_cmd; then
        log_success "数据持久化测试通过"
        return 0
    else
        log_error "数据持久化测试失败"
        return 1
    fi
}

# 运行所有验收测试
run_all_acceptance_tests() {
    log_info "运行完整的容器验收测试套件..."
    
    local overall_result=0
    
    # 运行编排测试
    if ! run_orchestration_tests; then
        overall_result=1
    fi
    
    # 运行性能测试
    if ! run_performance_tests; then
        overall_result=1
    fi
    
    # 运行数据持久化测试
    if ! run_persistence_tests; then
        overall_result=1
    fi
    
    return $overall_result
}

# 生成测试报告
generate_test_report() {
    log_info "生成测试报告..."
    
    local report_dir="test-reports/acceptance"
    mkdir -p "$report_dir"
    
    # 收集容器信息
    echo "=== 容器状态报告 ===" > "$report_dir/container_status.txt"
    docker compose -p "${PROJECT_NAME}" ps >> "$report_dir/container_status.txt" 2>&1 || true
    
    # 收集容器日志
    echo "=== 容器日志 ===" > "$report_dir/container_logs.txt"
    docker compose -p "${PROJECT_NAME}" logs >> "$report_dir/container_logs.txt" 2>&1 || true
    
    # 收集资源使用情况
    echo "=== 系统资源使用 ===" > "$report_dir/system_resources.txt"
    docker stats --no-stream >> "$report_dir/system_resources.txt" 2>&1 || true
    
    log_success "测试报告已生成到 $report_dir/"
}

# 主函数
main() {
    local run_orchestration=false
    local run_performance=false
    local run_persistence=false
    local run_all=false
    local cleanup_only=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --orchestration)
                run_orchestration=true
                shift
                ;;
            --performance)
                run_performance=true
                shift
                ;;
            --persistence)
                run_persistence=true
                shift
                ;;
            --all)
                run_all=true
                shift
                ;;
            --cleanup-only)
                cleanup_only=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定任何测试类型，显示帮助
    if [ "$run_orchestration" = false ] && [ "$run_performance" = false ] && [ "$run_persistence" = false ] && [ "$run_all" = false ] && [ "$cleanup_only" = false ]; then
        show_help
        exit 1
    fi
    
    # 执行清理
    if [ "$cleanup_only" = true ]; then
        cleanup_test_environment
        log_success "清理完成"
        exit 0
    fi
    
    log_info "开始容器验收测试..."
    
    # 设置错误处理
    trap cleanup_test_environment EXIT
    
    # 检查环境
    check_docker_environment
    check_dependencies
    
    # 清理并准备环境
    cleanup_test_environment
    setup_test_environment
    
    local test_result=0
    
    # 运行测试
    if [ "$run_all" = true ]; then
        if ! run_all_acceptance_tests; then
            test_result=1
        fi
    else
        if [ "$run_orchestration" = true ]; then
            if ! run_orchestration_tests; then
                test_result=1
            fi
        fi
        
        if [ "$run_performance" = true ]; then
            if ! run_performance_tests; then
                test_result=1
            fi
        fi
        
        if [ "$run_persistence" = true ]; then
            if ! run_persistence_tests; then
                test_result=1
            fi
        fi
    fi
    
    # 生成报告
    generate_test_report
    
    # 输出最终结果
    if [ $test_result -eq 0 ]; then
        log_success "所有容器验收测试通过！"
    else
        log_error "部分容器验收测试失败！"
    fi
    
    exit $test_result
}

# 运行主函数
main "$@" 