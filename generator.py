import sys
import yaml
from jinja2 import Environment, FileSystemLoader
import http.server
import re
from pathlib import Path
import random
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

class JinjaServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # pprint(self.requestline)
        # pprint(self.path)
        env = Environment(loader=FileSystemLoader("."))
        env.tests["list"] = is_list
        env.tests["dict"] = is_dict
        env.tests["tuple"] = is_tuple
        env.tests["str"] = is_str
        env.tests["collection"] = is_collection
        env.filters["prep_details"] = prep_details
        env.filters["clean_style"] = clean_quotes_and_dashes
        env.filters["convert_style"] = convert_quotes_and_dashes
        with open("resume.yaml") as fh:
            doc = yaml.safe_load(fh)

        if self.path == "/css":
            ext = "css"
        else:
            ext = "html"
        template = env.get_template(f"resume.{ext}.jinja2")
        self.send_response(200)
        self.send_header('Content-type', f'text/{ext}')
        self.end_headers()
        self.wfile.write(template.render(doc).encode('utf-8'))

if __name__ == "__main__":
    httpd = http.server.HTTPServer(('', 8080), JinjaServer)
    httpd.serve_forever()
