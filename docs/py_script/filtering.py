import json

from js import document, window
from pyodide.ffi import create_proxy


card_tag_cache = {}


def get_selected_filters():
    selected_by_group = {}
    for checkbox in document.querySelectorAll(
        "input[data-filter-group]:checked"
    ):
        group = checkbox.getAttribute("data-filter-group")
        value = checkbox.getAttribute("data-filter-value")
        selected_by_group.setdefault(group, set()).add(value)
    return selected_by_group


def apply_filters_and_sort(_event=None):
    grid = document.querySelector("#shoe-grid")
    if grid is None:
        return

    cards = list(grid.querySelectorAll(".product-card"))
    selected_by_group = get_selected_filters()
    visible_count = 0

    for card in cards:
        catalog_index = card.getAttribute("data-catalog-index")
        if catalog_index not in card_tag_cache:
            card_tag_cache[catalog_index] = json.loads(
                card.getAttribute("data-tags") or "{}"
            )
        tags = card_tag_cache[catalog_index]
        matches = all(
            selected_values.intersection(tags.get(group, []))
            for group, selected_values in selected_by_group.items()
        )
        card.hidden = not matches
        visible_count += int(matches)

    sort_mode = document.querySelector("#shoe-sort").value
    if sort_mode == "name-asc":
        cards.sort(key=lambda card: card.getAttribute("data-name").casefold())
    elif sort_mode in ("price-asc", "price-desc"):
        descending = sort_mode == "price-desc"

        def price_sort_key(card):
            price = card.getAttribute("data-price")
            if not price:
                return (True, 0)
            value = float(price)
            return (False, -value if descending else value)

        cards.sort(key=price_sort_key)
    else:
        cards.sort(key=lambda card: int(card.getAttribute("data-catalog-index")))

    if cards != list(grid.querySelectorAll(".product-card")):
        for card in cards:
            grid.append(card)

    status = document.querySelector("#filter-status")
    results = document.querySelector(".catalog-results")
    if results is not None:
        results.classList.toggle("is-empty", visible_count == 0)
    if status is not None:
        status.textContent = (
            f"Showing {visible_count} of {len(cards)} shoes"
            if visible_count
            else "No shoes match the selected filters."
        )


def on_catalog_ready(_event):
    apply_filters_and_sort()


def on_filter_change(event):
    if event.target.matches("input[data-filter-group]"):
        apply_filters_and_sort()


active_filter_details = None
active_filter_options = None


def position_active_filter_options(_event=None):
    if active_filter_details is None or active_filter_options is None:
        return

    summary = active_filter_details.querySelector("summary")
    bounds = summary.getBoundingClientRect()
    max_left = window.innerWidth - active_filter_options.offsetWidth - 16
    left = max(16, min(bounds.left, max_left))
    top = min(bounds.bottom + 4, window.innerHeight - 40)
    active_filter_options.style.left = f"{left}px"
    active_filter_options.style.top = f"{top}px"
    active_filter_options.style.maxHeight = f"{max(80, window.innerHeight - top - 16)}px"


def restore_active_filter_options():
    global active_filter_details, active_filter_options
    if active_filter_details is not None and active_filter_options is not None:
        active_filter_details.append(active_filter_options)
        active_filter_options.removeAttribute("style")
    active_filter_details = None
    active_filter_options = None


def activate_filter_options(details):
    global active_filter_details, active_filter_options
    if active_filter_details is not None and active_filter_details != details:
        active_filter_details.open = False
        restore_active_filter_options()

    options = details.querySelector(".filter-options")
    if options is None:
        return

    active_filter_details = details
    active_filter_options = options
    document.body.append(options)
    position_active_filter_options()


def sync_mobile_filter_menu(_event=None):
    if not window.matchMedia("(max-width: 640px)").matches:
        restore_active_filter_options()
        return

    if active_filter_details is not None and active_filter_details.open:
        return

    sidebar = document.querySelector(".filter-sidebar")
    opened_filter = sidebar.querySelector(".filter-section[open]") if sidebar else None
    if opened_filter is not None:
        activate_filter_options(opened_filter)


def handle_filter_toggle(event):
    details = event.currentTarget
    if details.open and window.matchMedia("(max-width: 640px)").matches:
        activate_filter_options(details)
    elif details == active_filter_details:
        restore_active_filter_options()


def handle_filter_click(event):
    if active_filter_details is None:
        return

    target = event.target
    summary = active_filter_details.querySelector("summary")
    if active_filter_options.contains(target) or summary.contains(target):
        return

    active_filter_details.open = False
    restore_active_filter_options()


filter_change_handler = create_proxy(on_filter_change)
sidebar = document.querySelector(".filter-sidebar")
if sidebar is not None:
    document.addEventListener("change", filter_change_handler)
    filter_toggle_handler = create_proxy(handle_filter_toggle)
    for details in sidebar.querySelectorAll(".filter-section"):
        details.addEventListener("toggle", filter_toggle_handler)
    filter_position_handler = create_proxy(position_active_filter_options)
    filter_resize_handler = create_proxy(sync_mobile_filter_menu)
    filter_click_handler = create_proxy(handle_filter_click)
    window.addEventListener("resize", filter_resize_handler)
    window.addEventListener("scroll", filter_position_handler)
    sidebar.addEventListener("scroll", filter_position_handler)
    document.addEventListener("click", filter_click_handler)
    sync_mobile_filter_menu()

sort_select = document.querySelector("#shoe-sort")
if sort_select is not None:
    sort_select.addEventListener("change", create_proxy(apply_filters_and_sort))

catalog_ready_handler = create_proxy(on_catalog_ready)
document.addEventListener("shoe-catalog-ready", catalog_ready_handler)
if document.querySelector("#shoe-grid .product-card") is not None:
    apply_filters_and_sort()
