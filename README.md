# Resume Generator

Part of the larger `resume-builder` project. You'll need a `.yaml` file with your resume and directory with `jinja2` templates.

## Setup
### .env file (optional)
  - `$ cp .env.example .env`
  - Fill in `resume_doc` with the path to your `.yaml` resume
  - If your templates are anywhere besides `../resume_template`, then fill in `template_path`
  - Add any fields to set defaults (instead of URL params) -- see comments for more info
  - Adjust the `chrome_bin` entry, if necessary
    - If you plan on saving out `.pdf` files and you are on macOS or linux, you will need to install Google Chrome.
    - If you're on linux or your Chrome installation is otherwise named differently, you'll need to update that entry.
    - Chromium _should probably_ work too, but I haven't tested it
    - If you plan on saving out `.pdf` files and you're __not__ on macOS or linux, I have no idea if it works or not. You're on your own.

### UV (optional, but recommended)
I recommend using `uv`, since it's the new python package management hotness. If you need to install `uv`, use your favorite platform-specific package manager (e.g. brew/apt/yum/apk/whatever-tf-windows-uses).

### pip/virtualenv (optional)
If you can't/won't install/learn `uv`, you can extract the dependencies from the config file with good ole' `sed`
```sh
$ sed -n '/dependencies/,/]/p' pyproject.toml | grep -o '"[^"]*"' | tr -d '"' > requirements.txt
```
...and then setup your virutal env
```sh
$ python -m venv venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

## Launching
### Using `uv`
```sh
$ uv run python generator.py
```

### Using venv/virutalenv (i.e. not using `uv`)
```sh
$ source .venv/bin/activate
python generator.py
```

## Running
There's currently no landing page. Just file URLs. The file path given in the URL is searched for in the templates directory with a `.jinja2` extension appended (except for fonts and other special cases). For example, if you have a template called `resume.html.jinja2`, then the url would be `http://localhost:8080/resume.html`.

Any config/environment variables can be overridden via the URL params as well. Note that when used as a url parameter, the varialbe `asciify_punctuation` becomes `ascii_punc`.

Load the URL in your favorite web browser and either **Save As...** or **Export As PDF...**.

### File types
### Special Caess: Fonts
The templates directory can include font files, which will be served as-is. The application will not try to append the `.jinja2` extension, as long as the mimetype of the extension resolves to a type of font.

#### Special Cases: PDF Files
If the URL file path has a `.pdf` extension, then the application will treat it as if the `.html` extension were given instead (when resolving to a template file), but before serving the file, the application will render the html to a `.pdf` file and serve that instead.

This can be useful if you generally use a browser that is "less than dilligent" about adhering to widely accepted web standards (cough... Safari! cough...), as those ignored formatting directives will be baked into the `.pdf` file upon export. (Safari also has a bad habit of ignoring certain formatting directives when exporting to `.pdf` even when they _were_ properly rendered in the WebView)

If you have Google Chrome installed on your system (and have it listed correctly in your config file), then the application will use Chrome (via it's CLI) to convert the html to pdf.

## Other Notes
### Template Variables
When building templates, the following variables will be injected into the jinja rendering environment:
  - `docname`: The filename (without path component or file extensions) of the template being rendered
  - `random`: a random number -- for circumventing file caching hijinx
  - `url_query_str`: The query string from the URL, as-is
The following variables will also be included (regardless of whether they were defined in the config or the URL params)
  - `indent_incr`
  - `bullet_char`
  - `prevent_breaks`
  - `asciify_punctuation`

## To Do
List of features to add
  - Replace `http.server` with a proper web server like `FastAPI` or `Flask`
  - Use pydantic's variable validation on URL parameters
  - A GUI of some sort (or TUI?)
  - AI Integration!
