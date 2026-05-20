"""Live feeds — dedicated navigation page."""


from app.page_shell import init_page
from app.views.live_feeds import render_live_feeds

init_page("live_feeds")
render_live_feeds(show_header=True)
