import os

log_file = r"d:\Work_Area\AI\API-Agent\api-platform\logs\modules\billing.log"

if os.path.exists(log_file):
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"=== billing.log 最后 30 行 ===")
        for line in lines[-30:]:
            print(line.rstrip())
else:
    print(f"日志文件不存在: {log_file}")
    # 列出 logs 目录下的文件
    import os
    for root, dirs, files in os.walk(r"d:\Work_Area\AI\API-Agent\api-platform\logs"):
        for f in files:
            if f.endswith('.log'):
                print(f"  {os.path.join(root, f)}")
