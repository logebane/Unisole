from js import document, window
from pyodide.ffi import create_proxy


callbacks = []
carousel_timer = None


def retain_callback(callback):
    proxy = create_proxy(callback)
    callbacks.append(proxy)
    return proxy


def play_video(video):
    if video.paused:
        video.play()


def sync_video_playback(video):
    slide = video.closest(".ad-carousel-slide")
    is_visible = video.getAttribute("data-carousel-visible") == "true"
    should_play = (
        slide is not None
        and slide.classList.contains("is-active")
        and is_visible
        and not document.hidden
    )
    if should_play and video.paused:
        play_video(video)
    elif not should_play and not video.paused:
        video.pause()


def show_slide(slides, indicators, index):
    if not slides:
        return

    active_index = index % len(slides)
    for slide_index, slide in enumerate(slides):
        is_active = slide_index == active_index
        slide.classList.toggle("is-active", is_active)
        slide.setAttribute("aria-hidden", str(not is_active).lower())
        video = slide.querySelector("video")
        if video is not None:
            sync_video_playback(video)
        indicators[slide_index].classList.toggle("is-active", is_active)
        if is_active:
            indicators[slide_index].setAttribute("aria-current", "true")
        else:
            indicators[slide_index].removeAttribute("aria-current")


def setup_video():
    carousel = document.querySelector(".ad-carousel")
    video = document.querySelector(".ad-carousel-slide video")
    watch_button = document.querySelector(".watch-campaign")
    if carousel is None or video is None or watch_button is None:
        return

    video.muted = True
    video.volume = 0.4
    video.setAttribute("data-carousel-visible", "false")

    def unmute_video():
        video.muted = False

    def watch_campaign(event):
        event.preventDefault()
        video.controls = True
        unmute_video()
        if hasattr(video, "requestFullscreen"):
            video.requestFullscreen()
        elif hasattr(video, "webkitEnterFullscreen"):
            video.webkitEnterFullscreen()
        play_video(video)

    def pause_when_not_visible(entries, _observer):
        video.setAttribute(
            "data-carousel-visible", str(entries[0].isIntersecting).lower()
        )
        sync_video_playback(video)

    def pause_when_page_hidden(_event):
        sync_video_playback(video)

    watch_button.addEventListener("click", retain_callback(watch_campaign))
    document.addEventListener(
        "visibilitychange", retain_callback(pause_when_page_hidden)
    )

    if hasattr(window, "IntersectionObserver"):
        observer_callback = retain_callback(pause_when_not_visible)
        observer = window.IntersectionObserver.new(observer_callback)
        observer.observe(carousel)
        callbacks.append(observer)
    else:
        video.setAttribute("data-carousel-visible", "true")
        sync_video_playback(video)


def setup_carousel():
    global carousel_timer

    carousel = document.querySelector(".ad-carousel")
    if carousel is None:
        return

    slides = list(carousel.querySelectorAll(".ad-carousel-slide"))
    indicators = list(carousel.querySelectorAll(".ad-carousel-indicators button"))
    if len(slides) != len(indicators):
        raise ValueError("Each advert slide must have a matching indicator.")

    active_index = 0
    reduced_motion = window.matchMedia("(prefers-reduced-motion: reduce)")
    autoplay_callback = None
    autoplay_enabled = True
    autoplay_button = carousel.querySelector(".ad-carousel-autoplay-toggle")

    def stop_autoplay(*_args):
        global carousel_timer
        if carousel_timer is not None:
            window.clearInterval(carousel_timer)
            carousel_timer = None

    def start_autoplay(*_args):
        global carousel_timer
        stop_autoplay()
        if autoplay_enabled and not reduced_motion.matches and len(slides) > 1:
            carousel_timer = window.setInterval(autoplay_callback, 6000)

    def toggle_autoplay(_event):
        nonlocal autoplay_enabled
        autoplay_enabled = not autoplay_enabled
        autoplay_button.setAttribute("aria-pressed", str(autoplay_enabled).lower())
        if autoplay_enabled:
            autoplay_button.setAttribute("aria-label", "Pause autoplay")
            start_autoplay()
        else:
            autoplay_button.setAttribute("aria-label", "Start autoplay")
            stop_autoplay()

    def advance_slide(change):
        nonlocal active_index
        active_index = (active_index + change) % len(slides)
        show_slide(slides, indicators, active_index)

    def show_selected_slide(event):
        nonlocal active_index
        indicator = event.currentTarget
        active_index = indicators.index(indicator)
        show_slide(slides, indicators, active_index)
        start_autoplay()

    autoplay_callback = retain_callback(lambda: advance_slide(1))

    def show_previous(_event):
        advance_slide(-1)
        start_autoplay()

    def show_next(_event):
        advance_slide(1)
        start_autoplay()

    previous_button = carousel.querySelector(".ad-carousel-previous")
    next_button = carousel.querySelector(".ad-carousel-next")
    autoplay_button.addEventListener("click", retain_callback(toggle_autoplay))
    previous_button.addEventListener("click", retain_callback(show_previous))
    next_button.addEventListener("click", retain_callback(show_next))
    for indicator in indicators:
        indicator.addEventListener("click", retain_callback(show_selected_slide))

    carousel.addEventListener("mouseenter", retain_callback(stop_autoplay))
    carousel.addEventListener("mouseleave", retain_callback(start_autoplay))
    carousel.addEventListener("focusin", retain_callback(stop_autoplay))

    def resume_after_focus(event):
        if event.relatedTarget is None or not carousel.contains(event.relatedTarget):
            start_autoplay()

    carousel.addEventListener("focusout", retain_callback(resume_after_focus))
    reduced_motion.addEventListener("change", retain_callback(start_autoplay))
    show_slide(slides, indicators, active_index)
    start_autoplay()


setup_video()
setup_carousel()
