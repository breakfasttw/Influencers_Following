import sys
# 解決 Python 3.12+ 缺失 distutils 的補丁
try:
    import distutils.version
except ImportError:
    import types
    d = types.ModuleType("distutils")
    v = types.ModuleType("distutils.version")
    class LooseVersion:
        def __init__(self, vstring): self.vstring = vstring
        def __str__(self): return self.vstring
    v.LooseVersion = LooseVersion
    d.version = v
    sys.modules["distutils"] = d
    sys.modules["distutils.version"] = v

import undetected_chromedriver as uc

def test_launch():
    options = uc.ChromeOptions()
    # 暫時不掛載你的 Profile 2，測試純淨啟動
    driver = uc.Chrome(use_subprocess=True) 
    driver.get("https://www.google.com")
    print("啟動成功！")
    driver.quit()

if __name__ == "__main__":
    test_launch()