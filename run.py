"""本地启动入口（需在仓库根目录执行）。生产环境推荐: python -m blog.main"""
import runpy

if __name__ == "__main__":
    runpy.run_module("blog.main", run_name="__main__")
