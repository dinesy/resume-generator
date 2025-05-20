import sys
import yaml
from jinja2 import Environment, FileSystemLoader
import http.server
import re
from pathlib import Path
import random
from urllib.parse import urlsplit, parse_qs
from pprint import pprint

"""
convert curly quotes to straight quotes and em and en dashes to hyphens
"""


def clean_quotes_and_dashes(text):
    if not text:
        return text
    text = re.sub(r"“|”", '"', text)
    text = re.sub(r"‘|’", "'", text)
    text = re.sub(r"—", "-", text)
    text = re.sub(r"–", "-", text)
    return text


"""
convert curly quotes and em and en dashes to proper HTML code
"""


def convert_quotes_and_dashes(text):
    if not text:
        return text
    text = text.replace("“", "&#147;")
    text = text.replace("”", "&#148;")
    text = text.replace("‘", "&#145;")
    text = text.replace("’", "&#146;")
    return text


"""
flatten lists of dictionaries to 1 list of k,v pairs
bare lists are (None, <list>)
scalars are (None, <scalar>)
"""


def prep_details(items):
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


class HandlerFactory:
    def __init__(self, yaml_path, jinja_env):
        self.yaml_path = yaml_path
        self.jinja_env = jinja_env

    def get_handler(self):
        factory = self

        class JinjaServer(http.server.BaseHTTPRequestHandler):
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
                            Path(factory.jinja_env.loader.searchpath[0]) / urlpath.name
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
                        reqfile = urlpath.name + ".jinja2"
                        if (
                            Path(factory.jinja_env.loader.searchpath[0]) / reqfile
                        ).is_file():
                            template = factory.jinja_env.get_template(reqfile)
                            with open(factory.yaml_path) as fh:
                                doc = yaml.safe_load(fh)
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

        return JinjaServer


if __name__ == "__main__":
    env = Environment(loader=FileSystemLoader(sys.argv[2]))
    env.tests["list"] = is_list
    env.tests["dict"] = is_dict
    env.tests["tuple"] = is_tuple
    env.tests["str"] = is_str
    env.tests["collection"] = is_collection
    env.filters["prep_details"] = prep_details
    env.filters["clean_style"] = clean_quotes_and_dashes
    env.filters["convert_style"] = convert_quotes_and_dashes

    httpd = http.server.HTTPServer(
        ("", 8080), HandlerFactory(sys.argv[1], env).get_handler()
    )
    httpd.serve_forever()
