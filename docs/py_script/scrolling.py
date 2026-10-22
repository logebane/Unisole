def init_header_scroll_behavior():
    from js import document, window
    from pyodide.ffi import create_proxy

    header = document.querySelector("header")
    back_to_top = document.querySelector(".back-to-top")
    mobile_menu = document.querySelector(".site-mobile-menu")
    previous_scroll_y = window.scrollY

    def handle_scroll(_event):
        nonlocal previous_scroll_y

        current_scroll_y = window.scrollY
        scrolling_down = current_scroll_y > previous_scroll_y
        if scrolling_down and mobile_menu is not None:
            mobile_menu.open = False

        if back_to_top is not None:
            back_to_top.classList.toggle("back-to-top-hidden", current_scroll_y <= 8)

        if current_scroll_y <= header.offsetHeight or not scrolling_down:
            header.classList.remove("header-hidden")
        else:
            header.classList.add("header-hidden")

        previous_scroll_y = current_scroll_y

    scroll_handler = create_proxy(handle_scroll)
    window.addEventListener("scroll", scroll_handler)
    handle_scroll(None)


init_header_scroll_behavior()
