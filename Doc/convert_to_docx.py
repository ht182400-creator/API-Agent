#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MD文件转Word文档转换器
"""

import os
import subprocess
import sys

workspace = 'c:/Users/ht182/CodeBuddy/20260416205552'
md_files = [f for f in os.listdir(workspace) if f.endswith('.md')]

print(f'开始转换 {len(md_files)} 个MD文件为Word格式...\n')

success_count = 0
fail_count = 0

for md_file in md_files:
    md_path = os.path.join(workspace, md_file)
    docx_file = md_file.replace('.md', '.docx')
    docx_path = os.path.join(workspace, docx_file)
    
    try:
        # 使用pandoc转换
        result = subprocess.run([
            'pandoc', 
            md_path, 
            '-o', docx_path,
            '--toc',
            '--toc-depth=3'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(docx_path):
            print(f'\u2713 {md_file} -> {docx_file}')
            success_count += 1
        else:
            print(f'\u2717 {md_file}: {result.stderr}')
            fail_count += 1
    except subprocess.TimeoutExpired:
        print(f'\u2717 {md_file}: 转换超时')
        fail_count += 1
    except Exception as e:
        print(f'\u2717 {md_file}: {str(e)}')
        fail_count += 1

print(f'\n转换完成: 成功 {success_count}, 失败 {fail_count}')
