import sys
import types
import yaml
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound
import http.server
import re
from pathlib import Path
import random
from urllib.parse import urlsplit, parse_qs
from pprint import pprint



def clean_quotes_and_dashes(text):
    """
    convert curly quotes to straight quotes and em and en dashes to hyphens
    """
    if not text:
        return text
    text = re.sub(r"“|”", '"', text)
    text = re.sub(r"‘|’", "'", text)
    text = re.sub(r"—", "-", text)
    text = re.sub(r"–", "-", text)
    return text


def convert_quotes_and_dashes(text):
    """
    convert curly quotes and em and en dashes to proper HTML code
    """
    if not text:
        return text
    text = text.replace("“", "&#147;")
    text = text.replace("”", "&#148;")
    text = text.replace("‘", "&#145;")
    text = text.replace("’", "&#146;")
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
            server_address, self.get_http_handler()
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

    def get_http_handler(self):
        parent = self

        class JinjaHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                urlparts = urlsplit(self.path)
                if urlparts.path == "/":
                    urlpath = Path("/resume.html")
                else:
                    urlpath = Path(urlparts.path)

                def str2num(val):
                    if val.isdigit():
                        return int(val)
                    if val.isdecimal():
                        return float(val)
                    return val

                def cvt_param(lst):
                    return (
                        str2num(lst[0])
                        if isinstance(lst, (list, tuple)) and len(lst) == 1
                        else list(map(str2num, lst))
                    )

                urlquery = {
                    k: cvt_param(v) for k, v in parse_qs(urlparts.query).items()
                }

                if len(urlpath.parts) >= 2:
                    if urlpath.parts[1] == "font":
                        font = (
                            Path(parent.jinja_env.loader.searchpath[0]) / urlpath.name
                        )
                        if font.is_file():
                            with font.open("rb") as fh:
                                self.send_response(200)
                                self.send_header(
                                    "Content-type",
                                    f"application/font-{font.suffix[1:]}",
                                )
                                self.end_headers()
                                self.wfile.write(fh.read())
                                return
                    else:
                        reqfile = urlpath.with_suffix(urlpath.suffix + ".jinja2")
                        try:
                            template = parent.jinja_env.get_template(str(reqfile))
                        except TemplateNotFound:
                            pass
                        else:
                            doc = parent.yaml_doc
                            self.send_response(200)
                            self.send_header(
                                "Content-type", f"text/{urlpath.suffix[1:]}"
                            )
                            self.end_headers()
                            vars = {
                                "docname": urlpath.stem,
                                "random": str(random.random())[2:],
                                "url_query": urlquery,
                                "url_query_str": urlparts.query,
                            }
                            self.wfile.write(
                                template.render(doc, **vars).encode("utf-8")
                            )
                            return
                self.send_error(404, f"File not found: {urlpath}")

        return JinjaHandler


if __name__ == "__main__":
    Generator(sys.argv[1], sys.argv[2], ("", 8080)).httpd.serve_forever()
