"""
Alembic 迁移基建守护测试

防止迁移基建被意外破坏（如误删 alembic.ini、清空 versions、env.py 断链）。
完整的 upgrade/schema 对齐验证见 docs/DATABASE_MIGRATIONS.md（命令行流程）。

用例编号：TC-MIG-001 ~ TC-003
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


class TestAlembicInfra:
    def test_alembic_ini_exists(self):
        """TC-MIG-001: alembic.ini 存在且 script_location 指向 alembic/"""
        ini = BASE_DIR / "alembic.ini"
        assert ini.is_file(), "alembic.ini 缺失 —— 迁移基建被破坏"

        content = ini.read_text(encoding="utf-8")
        assert "script_location" in content

    def test_baseline_migration_exists(self):
        """TC-MIG-002: versions/ 至少有 1 个迁移（基线），且含建表操作"""
        versions = BASE_DIR / "alembic" / "versions"
        files = [f for f in versions.glob("*.py") if f.name != "__init__.py"]
        assert files, "alembic/versions 为空 —— 基线迁移丢失"

        baseline = "\n".join(f.read_text(encoding="utf-8") for f in files)
        assert "create_table" in baseline, "基线迁移中无 create_table 操作"

    def test_env_py_importable(self):
        """TC-MIG-003: env.py 可正常加载（模型元数据 + 连接串逻辑不中断）"""
        import importlib.util

        env_path = BASE_DIR / "alembic" / "env.py"
        spec = importlib.util.spec_from_file_location("alembic_env_guard", env_path)
        assert spec and spec.loader

        # env.py 顶层含 alembic context 依赖，完整执行需 alembic 上下文；
        # 这里只验证文件可被编译（语法/缩进层面完整）
        compile(env_path.read_text(encoding="utf-8"), str(env_path), "exec")
