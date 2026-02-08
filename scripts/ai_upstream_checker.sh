#!/bin/bash
#===============================================================================
# Gentoo AI 上游版本检查器
#
# 功能: 使用AI自动检查Gentoo软件包的上游版本
# 模型: k2.5 free (通过Perplexity/Firecrawl)
#
# 用法:
#   ./ai_upstream_checker.sh              # 检查所有配置的包
#   ./ai_upstream_checker.sh <包名>       # 检查单个包
#   ./ai_upstream_checker.sh --report    # 生成报告
#===============================================================================

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/scripts/ai_upstream_checker.py"
LOG_DIR="${SCRIPT_DIR}/logs"
DATA_DIR="${SCRIPT_DIR}/data"
CONFIG_FILE="${DATA_DIR}/packages_to_monitor.txt"

# 创建必要的目录
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

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

# 显示帮助
show_help() {
	cat <<EOF
Gentoo AI 上游版本检查器

用法: $0 [选项] [包名]

选项:
    -h, --help          显示此帮助信息
    -r, --report        生成检查报告
    -c, --config        指定配置文件
    -v, --verbose       显示详细输出
    --cache-clear       清除版本缓存
    --single <包名>     检查单个包

示例:
    $0                  # 检查所有配置的包
    $0 app-editors/neovim    # 检查neovim
    $0 --report         # 生成报告
    $0 --cache-clear    # 清除缓存后重新检查
EOF
}

# 检查Python依赖
check_dependencies() {
	log_info "检查Python环境..."

	# 检查Python 3
	if ! command -v python3 &>/dev/null; then
		log_error "Python 3 未安装!"
		exit 1
	fi

	log_success "Python 3 已安装"
}

# 主检查函数
run_check() {
	local package="${1:-}"
	local verbose="${2:-false}"

	log_info "开始上游版本检查..."
	log_info "使用模型: k2.5 free"
	echo ""

	# 构建Python命令
	local cmd="python3 ${PYTHON_SCRIPT}"

	if [ -n "$package" ]; then
		cmd="${cmd} ${package}"
	fi

	if [ "$verbose" == "true" ]; then
		cmd="${cmd} --verbose"
	fi

	# 执行检查
	if eval "$cmd"; then
		log_success "检查完成"
	else
		log_error "检查过程中出现错误"
		return 1
	fi
}

# 生成报告
generate_report() {
	log_info "生成检查报告..."

	# 查找最新的检查结果
	local latest_log=$(find "${LOG_DIR}" -name "check_result_*.json" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

	if [ -z "$latest_log" ] || [ ! -f "$latest_log" ]; then
		log_warning "未找到检查结果，请先运行检查"
		return 1
	fi

	log_info "使用结果文件: $latest_log"

	# 生成Markdown报告
	python3 -c "
import json
import sys

log_file = '$latest_log'
report_file = '${LOG_DIR}/report_$(date +%Y%m%d_%H%M%S).md'

with open(log_file, 'r') as f:
    data = json.load(f)

with open(report_file, 'w') as f:
    f.write('# Gentoo AI 包维护报告\\n')
    f.write(f'生成时间: $(date)\\n\\n')
    
    f.write('## 统计信息\\n')
    f.write(f'- 总包数: {data.get(\"total_packages\", 0)}\\n')
    f.write(f'- 需要更新: {data.get(\"needs_update\", 0)}\\n')
    f.write(f'- 已是最新: {data.get(\"up_to_date\", 0)}\\n')
    f.write(f'- 检查失败: {data.get(\"failed\", 0)}\\n\\n')
    
    if data.get('packages'):
        f.write('## 需要更新的包\\n\\n')
        f.write('| 包名 | 当前版本 | 最新版本 | 置信度 | 状态 |\\n')
        f.write('|------|----------|----------|--------|------|\\n')
        
        for pkg in data.get('packages', []):
            status = '✅' if pkg.get('needs_update') else '⏸️'
            confidence = pkg.get('confidence', 0)
            f.write(f\"{pkg.get('package', 'N/A')} | {pkg.get('current_version', 'N/A')} | {pkg.get('latest_version', 'N/A')} | {confidence:.0%} | {status}\\n\")
    
    f.write('\\n---\\n')
    f.write('由 Gentoo AI 包维护系统自动生成\\n')

print(f\"报告已生成: {report_file}\")
"

	log_success "报告已生成"
}

# 清除缓存
clear_cache() {
	log_info "清除版本缓存..."

	local cache_file="${DATA_DIR}/version_cache.json"

	if [ -f "$cache_file" ]; then
		rm -f "$cache_file"
		log_success "缓存已清除"
	else
		log_warning "没有找到缓存文件"
	fi
}

# 主程序
main() {
	local action="check"
	local package=""
	local verbose=false

	# 解析参数
	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			show_help
			exit 0
			;;
		-r | --report)
			action="report"
			shift
			;;
		-c | --config)
			CONFIG_FILE="$2"
			shift 2
			;;
		-v | --verbose)
			verbose=true
			shift
			;;
		--cache-clear)
			action="clear"
			shift
			;;
		--single)
			package="$2"
			shift 2
			;;
		-*)
			log_error "未知选项: $1"
			show_help
			exit 1
			;;
		*)
			package="$1"
			shift
			;;
		esac
	done

	# 执行操作
	case $action in
	check)
		check_dependencies
		run_check "$package" "$verbose"
		;;
	report)
		generate_report
		;;
	clear)
		clear_cache
		;;
	esac
}

# 运行主程序
main "$@"
