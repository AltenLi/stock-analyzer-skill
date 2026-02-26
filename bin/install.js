#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const SKILL_NAME = 'stock-analyzer';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  red: '\x1b[31m',
  cyan: '\x1b[36m'
};

function log(msg, color = 'reset') {
  console.log(`${colors[color]}${msg}${colors.reset}`);
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  
  if (stat.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    const files = fs.readdirSync(src);
    files.forEach(file => {
      // 跳过隐藏文件
      if (file.startsWith('.')) return;
      copyRecursive(path.join(src, file), path.join(dest, file));
    });
  } else {
    fs.copyFileSync(src, dest);
  }
}

function install() {
  log('\n📊 Stock Analyzer Skill 安装程序', 'cyan');
  log('================================\n', 'cyan');

  // 确定目标目录
  const cwd = process.cwd();
  const targetDir = path.join(cwd, '.codebuddy', 'skills', SKILL_NAME);

  // 源skill目录
  const sourceDir = path.join(__dirname, '..', 'skill');

  // 检查源目录是否存在
  if (!fs.existsSync(sourceDir)) {
    log('❌ 错误：找不到skill源文件', 'red');
    process.exit(1);
  }

  // 检查是否已安装
  if (fs.existsSync(targetDir)) {
    log(`⚠️  Skill已存在于: ${targetDir}`, 'yellow');
    log('   如需重新安装，请先删除该目录\n', 'yellow');
    
    const readline = require('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });
    
    rl.question('是否覆盖安装？(y/N): ', (answer) => {
      rl.close();
      if (answer.toLowerCase() === 'y') {
        fs.rmSync(targetDir, { recursive: true, force: true });
        performInstall(sourceDir, targetDir, cwd);
      } else {
        log('\n❌ 安装已取消\n', 'yellow');
        process.exit(0);
      }
    });
  } else {
    performInstall(sourceDir, targetDir, cwd);
  }
}

function performInstall(sourceDir, targetDir, cwd) {
  try {
    // 创建目标目录
    fs.mkdirSync(targetDir, { recursive: true });

    // 复制skill文件
    log('📁 正在复制文件...', 'blue');
    copyRecursive(sourceDir, targetDir);

    log('\n✅ 安装成功！\n', 'green');
    log(`📍 安装位置: ${targetDir}`, 'cyan');
    log('\n📖 使用方法:', 'yellow');
    log('   在CodeBuddy中输入以下关键词即可触发:', 'reset');
    log('   - "分析股票 [股票名称]"', 'reset');
    log('   - "帮我分析一下 [股票名称]"', 'reset');
    log('   - "股票推荐"、"股票买卖点"\n', 'reset');

    log('📊 功能特点:', 'yellow');
    log('   - 基本面分析 (35%): PE/PB、ROE、成长性', 'reset');
    log('   - 新闻面分析 (20%): 公告、研报、舆情', 'reset');
    log('   - 资金面分析 (35%): 主力净比(核心)、北向资金', 'reset');
    log('   - 技术面分析 (10%): 均线、支撑压力位\n', 'reset');

    log('⚠️  注意事项:', 'yellow');
    log('   - 建议先登录东方财富网以获取完整数据', 'reset');
    log('   - 本工具仅供参考，不构成投资建议\n', 'reset');

  } catch (err) {
    log(`\n❌ 安装失败: ${err.message}`, 'red');
    process.exit(1);
  }
}

// 处理命令行参数
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  log('\n📊 Stock Analyzer Skill', 'cyan');
  log('========================\n', 'cyan');
  log('用法: npx @altenli/stock-analyzer-skill [选项]\n', 'reset');
  log('选项:', 'yellow');
  log('  --help, -h     显示帮助信息', 'reset');
  log('  --version, -v  显示版本号\n', 'reset');
  log('说明:', 'yellow');
  log('  运行此命令会将skill安装到当前目录的', 'reset');
  log('  .codebuddy/skills/stock-analyzer/ 下\n', 'reset');
  process.exit(0);
}

if (args.includes('--version') || args.includes('-v')) {
  const pkg = require('../package.json');
  log(`v${pkg.version}`, 'green');
  process.exit(0);
}

// 执行安装
install();
