from playwright.sync_api import TimeoutError, expect, sync_playwright
from utils.trace_cleaner import trace_cleaner

# Expensify app URL
EXPENSIFY_URL = "https://dev.new.expensify.com:8082/"

# Email login credentials
EMAIL_USERNAME = "expensifytesting1@gmail.com"
EMAIL_PASSWORD = "redx tbmr hzpc rbzr"

# Email username postfix
EMAIL_USERNAME_POSTFIX = "52923.3"


def generate_user_email(user_id=None):
    """
    Generate an email address for user login.
    """
    temp = EMAIL_USERNAME.rsplit("@", 1)
    username = temp[0].strip()
    domain = temp[1].strip()
    return f"{username}+{EMAIL_USERNAME_POSTFIX}{user_id or ''}@{domain}"


def launch_browser(pw, headless=False, device=None, permissions=None, geolocation=None):
    """
    Launch the browser.
    """
    browser = pw.chromium.launch(
        channel="chrome",
        headless=headless,
        args=[
            "--ignore-certificate-errors",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ],
        slow_mo=1000,
    )
    context_args = {"permissions": permissions or []}
    if device:
        context_args.update(pw.devices[device])
    if geolocation:
        context_args["geolocation"] = geolocation
        context_args["permissions"].append("geolocation")
    context = browser.new_context(**context_args)
    page = context.new_page()
    return browser, context, page


def login_user(page, user_email, first_name="John", last_name="Doe"):
    """
    Log into the Expensify app.
    """
    # Open the Expensify app
    page.goto(EXPENSIFY_URL)
    # Login user
    page.get_by_test_id("username").fill(user_email)
    page.get_by_role("button", name="Continue").click()
    # Check if OTP is required for the login
    try:
        expect(page.get_by_test_id("SignInPage").get_by_test_id("validateCode")).to_be_visible(timeout=7000)
    except (AssertionError, TimeoutError):
        # If not required, expect the join button to appear and click the button
        page.get_by_test_id("SignInPage").get_by_role("button", name="Join").click()
    else:
        # Get the OTP and complete verification
        otp_code = "123456"
        page.get_by_test_id("SignInPage").get_by_test_id("validateCode").fill(otp_code)
        try:
            page.get_by_test_id("SignInPage").get_by_role("button", name="Sign in").click(timeout=2000)
        except (AssertionError, TimeoutError):
            pass
    # Check if onboarding is required
    try:
        expect(page.get_by_text("What do you want to do today?")).to_be_visible(timeout=5000)
    except (AssertionError, TimeoutError):
        pass
    else:
        # Complete the onboarding
        page.get_by_label("Track and budget expenses").click()
        page.get_by_role("button", name="Continue").first.click()
        page.get_by_role("textbox", name="First name").fill(first_name)
        page.get_by_role("textbox", name="Last name").fill(last_name)
        page.get_by_role("button", name="Continue").last.click()
    # Dismiss get started dialog if appears
    try:
        page.get_by_role("button", name="Get started").click(timeout=3000)
    except (AssertionError, TimeoutError):
        pass
    # Expect the main screen to appear
    expect(page.get_by_test_id("BaseSidebarScreen")).to_be_visible(timeout=7000)
    # Close the info message if appears
    try:
        page.get_by_role("button", name="Close").click(timeout=2000)
    except (AssertionError, TimeoutError):
        pass


def test_search_query():
    """
    Verify that the search query will not change on switching status.
    """
    with sync_playwright() as pw:
        # Login user
        user_email = generate_user_email()
        browser, context, page = launch_browser(pw)
        # Start tracing before running test steps
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        try:
            login_user(page, user_email)

            # Go to search
            page.get_by_test_id("CustomBottomTabNavigator").get_by_role("button", name="Reports").click()
            # Close the info message if it appears
            try:
                page.get_by_role("button", name="Close").click(timeout=4000)
            except (AssertionError, TimeoutError):
                pass

            # Set search filter and view results
            search_term = "https://google.com/"
            page.get_by_test_id("Search").get_by_role("button", name="Filters").click()
            page.get_by_test_id("SearchAdvancedFiltersPage").get_by_role("menuitem", name="Has Keywords").click()
            page.get_by_test_id("SearchFiltersKeywordPage").get_by_role("textbox", name="Keyword").fill(search_term)
            page.get_by_test_id("SearchFiltersKeywordPage").get_by_role("button", name="Save").click()
            page.get_by_test_id("SearchAdvancedFiltersPage").get_by_role("button", name="View results").click()

            # Read the search query
            search_query = page.get_by_test_id("Search").get_by_role("textbox", name="Search for something").input_value()
            search_query = search_query.split(" ")[-1]

            # Switch status multiple times
            page.get_by_test_id("Search").get_by_role("button", name="Approved").click()
            page.get_by_test_id("Search").get_by_role("button", name="Outstanding").click()
            page.get_by_test_id("Search").get_by_role("button", name="Drafts").click()
            page.get_by_test_id("Search").get_by_role("button", name="All").click()

            # Read the search query again
            search_query_1 = page.get_by_test_id("Search").get_by_role("textbox", name="Search for something").input_value()
            search_query_1 = search_query_1.split(" ")[-1]

            # Verify that the search query has not changed
            assert search_query == search_query_1, "Search query must not change on switching status"
        finally:
            # Stop tracing and export the trace file
            context.tracing.stop(path="/app/expensify/user_tool/output_browser1.zip")
            trace_cleaner("/app/expensify/user_tool/output_browser1.zip")
            browser.close()


if __name__ == "__main__":
    test_search_query()
