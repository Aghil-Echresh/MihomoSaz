import os
import re
import urllib.parse
import logging
from typing import List, Tuple

# تنظیمات لاگ
logging.basicConfig(
    filename="update.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

class ConfigProcessor:
    def __init__(self):
        self.template_path = "mihomo_template.txt"
        self.output_dir = "Sublist"
        self.readme_path = "README.md"
        self.base_url = "https://raw.githubusercontent.com/10ium/MihomoSaz/main/Sublist/"
        self.simple_list = "Simple_URL_List.txt"
        self.complex_list = "Complex_URL_list.txt"

    def _process_url(self, url: str, is_complex: bool) -> str:
        """پردازش URL بر اساس نوع لیست"""
        if is_complex:
            encoded = urllib.parse.quote(url, safe=':/?&=')
            return (
                "https://revil-sub.pages.dev/sub/clash-meta?"
                f"{encoded}&target=clash&config="
                "https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FSleepyHeeead"
                "%2Fsubconverter-config%40master%2Fremote-config"
                "%2Funiversal%2Furltest.ini&emoji=false"
                "&append_type=true&append_info=true&scv=true"
                "&udp=true&list=true&sort=false&fdn=true"
                "&insert=false"
            )
        return url

    def _load_entries(self, file_path: str, is_complex: bool) -> List[Tuple[str, str]]:
        """بارگذاری لیست URLها"""
        entries = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "|" not in line:
                        continue
                    filename, url = line.strip().split("|", 1)
                    processed_url = self._process_url(url.strip(), is_complex)
                    entries.append((filename.strip(), processed_url))
        except FileNotFoundError:
            logging.error(f"فایل {file_path} یافت نشد!")
        return entries

    def _replace_proxy_url(self, template: str, new_url: str) -> str:
        """جایگزینی URL در بخش proxy-providers"""
        pattern = re.compile(
            r'(proxy-providers:\s*\n\s+proxy:\s*\n\s+type:\s*http\s*\n\s+url:\s*>?-?\s*\n\s+)([^\n]+)',
            re.DOTALL
        )
        return pattern.sub(rf'\g<1>{new_url}', template)

    def _replace_proxy_path(self, template: str, new_path: str) -> str:
        """جایگزینی path در بخش proxy-providers با دقت"""
        # این الگو به دنبال خط 'include-all:' می‌گردد و سپس خط 'path:' را در خط بعدی جایگزین می‌کند.
        pattern = re.compile(
            r"(\n\s+include-all:\s*(?:true|false)\s*\n\s+path:\s*)([^\n]+)",
            re.IGNORECASE
        )
        return pattern.sub(rf'\g<1>{new_path}', template, count=1)

    def _generate_aggregate(self, entries: List[Tuple[str, str]], template: str) -> None:
        """ساخت یک کانفیگ واحد Mihomo/Clash Meta با همه Providerها."""
        provider_blocks = []
        provider_names = []
        for idx, (_, url) in enumerate(entries, 1):
            name = "proxy" if idx == 1 else f"p{idx:03d}"
            provider_names.append(name)
            provider_blocks.append(
                f"  {name}:\n"
                f"    type: http\n"
                f"    url: {url}\n"
                f"    interval: 86400\n"
                f"    include-all: true\n"
                f"    path: ./providers/{name}.yaml\n"
                f"    health-check:\n"
                f"      enable: true\n"
                f"      interval: 1800\n"
                f"      url: \"https://www.gstatic.com/generate_204\"\n"
            )
        section = "proxy-providers:\n\n" + "\n".join(provider_blocks) + "\n\nrules:"
        modified = re.sub(r"proxy-providers:\s*\n.*?\n\s*rules:", section, template, count=1, flags=re.DOTALL)
        use_block = "use:\n" + "".join(f"      - {name}\n" for name in provider_names)
        modified = re.sub(r"use:\s*\n\s+- proxy\s*\n", use_block, modified)
        with open(self.aggregate_path, "w", encoding="utf-8") as f:
            f.write(modified)

    def _write_status(self, simple_count: int, complex_count: int, total_count: int) -> None:
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "simple": simple_count,
            "complex": complex_count,
            "total": total_count
        }
        with open(self.status_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_readme(self, entries: List[Tuple[str, str]]) -> None:
        """تولید README با لینک مستقیم"""
        md_content = [
            "# 📂 لیست کانفیگ‌های کلش متا",
            "### با قوانین مخصوص ایران\n",
            "**فایل‌های پیکربندی آماده استفاده:**\n"
        ]
        
        emojis = ["🌐", "🚀", "🔒", "⚡", "🛡️"]
        for idx, (filename, _) in enumerate(entries):
            emoji = emojis[idx % len(emojis)]
            file_url = f"{self.base_url}{urllib.parse.quote(filename)}"
            md_content.append(f"- [{emoji} {filename}]({file_url})")

        md_content.extend([
            "\n## 📖 راهنمای استفاده",
            "1. روی لینک مورد نظر **کلیک راست** کنید",
            "2. گزینه **«کپی لینک»** را انتخاب کنید",
            "3. لینک را در کلش متا **وارد کنید**\n",
    
            "## ⭐ ویژگی‌ها",
            "- 🚀 بهینه‌شده برای ایران",
            "- 🔄 فعال و غیر فعال کردن راحت قوانین",
            "- 📆 آپدیت روزانه\n",
    
            "## 📥 دریافت کلاینت",
            "### ویندوز",  
            "[Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev/releases)",
    
            "### اندروید",
            "[ClashMeta for Android](https://github.com/MetaCubeX/ClashMetaForAndroid/releases)"
        ])

        with open(self.readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

    def generate_configs(self):
        """تولید فایل‌های پیکربندی"""
        # بارگذاری لیست‌ها
        simple_entries = self._load_entries(self.simple_list, False)
        complex_entries = self._load_entries(self.complex_list, True)
        
        # ادغام با اولویت ساده
        merged = {}
        for name, url in simple_entries + complex_entries:
            if name not in merged:
                merged[name] = url

        # خواندن تمپلیت اصلی
        with open(self.template_path, "r", encoding="utf-8") as f:
            original_template = f.read()

        # ساخت پوشه‌ی خروجی اصلی
        os.makedirs(self.output_dir, exist_ok=True)
        
        # تبدیل دیکشنری به لیست برای داشتن ترتیب ثابت و ایندکس
        merged_items = list(merged.items())

        for idx, (filename, url) in enumerate(merged_items):
            # مرحله ۱: جایگزینی URL پروکسی
            modified = self._replace_proxy_url(original_template, url)
            
            # مرحله ۲: ساخت path جدید و جایگزینی آن در محتوای تغییر یافته
            new_path = f"./MihomoSaz{idx + 1}.yaml"
            modified = self._replace_proxy_path(modified, new_path)

            output_path = os.path.join(self.output_dir, filename)
            
            # اطمینان از وجود دایرکتوری‌های میانی مسیر خروجی
            dir_path = os.path.dirname(output_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # نوشتن فایل خروجی
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(modified)

        # تولید README، اشتراک واحد و وضعیت
        self._generate_readme(merged_items)
        self._generate_aggregate(merged_items, original_template)
        self._write_status(len(simple_entries), len(complex_entries), len(merged_items))
        logging.info("فایل‌ها، اشتراک واحد و وضعیت با موفقیت ساخته شدند!")

if __name__ == "__main__":
    try:
        processor = ConfigProcessor()
        processor.generate_configs()
        logging.info("✅ پردازش با موفقیت انجام شد!")
    except Exception as e:
        logging.critical(f"❌ خطا: {e}", exc_info=True)
