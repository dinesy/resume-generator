import sys
import types
import yaml
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
import http.server
import re
from pathlib import Path
import random
from urllib.parse import urlsplit, urlunsplit, parse_qs
import tempfile
import shlex
import subprocess
from pprint import pprint

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class Defaults:
    indent_incr = 2
    bullet_char = "*"
    prevent_breaks = True


def chrome_pdf_convert(input, pdf_path, esc=False):
    cmd = [
        CHROME_BIN,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        input,
    ]
    if esc:
        cmd = list(map(shlex.quote, cmd))
    return cmd


def clean_quotes_and_dashes(text):
    """
    convert curly quotes to straight quotes and em and en dashes to hyphens
    """
    if not text:
        return text
    text = re.sub(r"“|”", '"', text)
    text = re.sub(r"‘|’", "'", text)
    text = re.sub(r"—", "--", text)
    # text = text.replace("—", "--")
    text = re.sub(r"–", "-", text)
    return text


def convert_quotes_and_dashes(text):
    """
    convert curly quotes and em and en dashes to proper HTML code
    """
    if not text:
        return text
    text = text.replace("“", "&ldquo;")
    text = text.replace("”", "&rdquo;")
    text = text.replace("‘", "&lsquo;")
    text = text.replace("’", "&rsquo;")
    text = text.replace("–", "&ndash;")
    text = text.replace("—", "&mdash;")
    text = text.replace("…", "&hellip;")
    return text


def prep_details(items):
    """
    flatten lists of dictionaries to 1 list of k,v pairs
    bare lists are (None, <list>)
    scalars are (None, <scalar>)
    """
    # if is_str(items):
    #     return items
    result = []
    use_tuples = False
    # if isinstance(items, (dict, tuple)):
    if is_dict(items):
        items = [items]
        use_tuples = True
    elif not is_list(items):
        return items
    # elif len(items) == 1:
    #     return items[0]
    for item in items:
        if is_list(item):
            # if len(item) <= 1:
            #     result.extend(prep_details(item))
            if use_tuples:
                result.append((None, prep_details(item)))
            else:
                result.append(prep_details(item))
        elif is_dict(item):
            use_tuples = True
            result.extend((k, prep_details(v)) for k, v in item.items())
        else:
            result.append((None, item) if use_tuples else item)
    # if len(result) == 1 and use_tuples:
    #     return result[0]
    return result


def is_instance(item, typ):
    # pprint(vars())
    if not isinstance(typ, (list, tuple)):
        typ = (typ,)
    typ = tuple(globals()[t] if isinstance(t, str) else t for t in typ)
    return isinstance(item, typ)


def is_str(item):
    return is_instance(item, str)


def is_list(item):
    return is_instance(item, list)


def is_tuple(item):
    return is_instance(item, tuple)


def is_collection(item):
    return is_instance(item, (list, tuple, set, dict))


def is_dict(item):
    return is_instance(item, dict)


def yaml_load(path):
    with open(path) as fh:
        return yaml.safe_load(fh.read())


class Generator:
    def __init__(self, yaml_path, jinja_path, server_address=("localhost", 8080)):
        self._yaml_path = yaml_path
        self._jinja_env = lambda: Environment(loader=FileSystemLoader(jinja_path))
        self._httpd = lambda: http.server.ThreadingHTTPServer(
            server_address, self._create_http_handler()
        )

    @property
    def yaml_doc(self):
        return yaml_load(self._yaml_path)

    @property
    def jinja_env(self):
        if isinstance(self._jinja_env, types.FunctionType):
            self._jinja_env = self._jinja_env()
            self._jinja_env.tests["list"] = is_list
            self._jinja_env.tests["dict"] = is_dict
            self._jinja_env.tests["tuple"] = is_tuple
            self._jinja_env.tests["str"] = is_str
            self._jinja_env.tests["collection"] = is_collection
            self._jinja_env.filters["prep_details"] = prep_details
            self._jinja_env.filters["clean_style"] = clean_quotes_and_dashes
            self._jinja_env.filters["convert_style"] = convert_quotes_and_dashes
        return self._jinja_env

    @property
    def httpd(self):
        if isinstance(self._httpd, types.FunctionType):
            self._httpd = self._httpd()
        return self._httpd

    @property
    def server_address(self):
        if self._httpd is None:
            return
        return "http://" + ":".join(map(str, self.httpd.server_address)).replace(
            "0.0.0.0", "localhost"
        )

    def _create_http_handler(self):
        generator = self

        class JinjaHandler(AbsJinjaHandler):
            @property
            def _generator(self):
                return generator

        return JinjaHandler


class AbsJinjaHandler(http.server.BaseHTTPRequestHandler):
    @classmethod
    def str2num(cls, val):
        if val.isdigit():
            return int(val)
        if val.isdecimal():
            return float(val)
        return val

    @classmethod
    def cvt_param(cls, lst):
        if isinstance(lst, (list, tuple)) and len(lst) == 1:
            return cls.str2num(lst[0])
        else:
            list(map(cls.str2num, lst))

    @property
    def _generator(self):
        raise NotImplementedError()

    @property
    def urlparts(self):
        return urlsplit(self.path)

    @property
    def urlpath(self):
        if self.urlparts.path == "/":
            return Path("/resume.html")
        else:
            return Path(self.urlparts.path)

    @property
    def urlquery(self):
        return {k: self.cvt_param(v) for k, v in parse_qs(self.urlparts.query).items()}

    def do_GET(self):
        if len(self.urlpath.parts) >= 2:
            if self.urlpath.parts[1] == "font":
                font = (
                    Path(self._generator.jinja_env.loader.searchpath[0])
                    / self.urlpath.name
                )
                if font.is_file():
                    with font.open("rb") as fh:
                        self.send_response(200)
                        self.send_header(
                            "Content-type",
                            f"application/font-{font.suffix[1:]}",
                        )
                        self.end_headers()
                        self.wfile._sock.sendfile(fh)
                        return
            elif self.urlpath.suffix == ".pdf":
                html_path = self.urlpath.with_suffix(".html")
                html_url = self._generator.server_address + urlunsplit(
                    self.urlparts._replace(path=str(html_path))
                )
                mimetype = "application/pdf"
                with tempfile.NamedTemporaryFile(
                    "r+b", suffix=".pdf", prefix="resume_", delete=False
                ) as pdftmp:
                    cmd = chrome_pdf_convert(html_url, pdftmp.name, esc=False)
                    proc = subprocess.Popen(
                        cmd,
                        shell=False,
                        start_new_session=True,
                    )
                    proc.wait()
                    subprocess.Popen(["ls", "-l", pdftmp.name])
                    self.send_response(200)
                    self.send_header("Content-type", mimetype)
                    self.send_header(
                        "Content-Disposition",
                        f"filename={self.urlpath.name}",
                    )
                    self.end_headers()
                    self.wfile._sock.sendfile(pdftmp)
                return
            else:
                reqfile = self.urlpath.with_suffix(self.urlpath.suffix + ".jinja2")
                mimetype = f"text/{self.urlpath.suffix[1:]}; charset=utf-8"
                try:
                    template = self._generator.jinja_env.get_template(str(reqfile))
                except TemplateNotFound:
                    pass
                else:
                    doc = self._generator.yaml_doc
                    vars = {
                        "docname": self.urlpath.stem,
                        "random": str(random.random())[2:],
                        "indent_incr": self.urlquery.get(
                            "indent_incr", Defaults.indent_incr
                        ),
                        "bullet_char": self.urlquery.get(
                            "bullet_char", Defaults.bullet_char
                        ),
                        "prevent_breaks": bool(
                            self.urlquery.get("prevent_breaks", Defaults.prevent_breaks)
                        ),
                        "url_query_str": self.urlparts.query,
                    }
                    rendered_doc = template.render(doc, **vars)
                    self.send_response(200)
                    self.send_header("Content-type", mimetype)
                    self.end_headers()
                    self.wfile.write(rendered_doc.encode("utf-8"))
                    return
        self.send_error(404, f"File not found: {self.urlpath}")


if __name__ == "__main__":
    Generator(sys.argv[1], sys.argv[2], ("", 8080)).httpd.serve_forever()
