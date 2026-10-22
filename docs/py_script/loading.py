from js import document, window
from pyodide.ffi import create_proxy


def hide_site_loader(_event=None):
    loader = document.querySelector("#site-loader")
    if loader is not None:
        loader.classList.add("site-loader-hidden")


def handle_window_load(_event=None):
    body = document.body
    if body is not None and body.getAttribute("data-loader-mode") == "shoe-data":
        return
    hide_site_loader()


window_load_handler = create_proxy(handle_window_load)
shoe_data_handler = create_proxy(hide_site_loader)

window.addEventListener("load", window_load_handler)
document.addEventListener("shoe-data-ready", shoe_data_handler)
document.addEventListener("shoe-data-error", shoe_data_handler)

body = document.body
if body is not None:
    if body.getAttribute("data-loader-mode") == "shoe-data":
        if body.getAttribute("data-shoe-data-state") in ("ready", "error"):
            hide_site_loader()
    elif document.readyState == "complete":
        hide_site_loader()
