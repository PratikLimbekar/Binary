# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time

# def playytmusic(query: str) -> str:
#     try:
#         options = webdriver.ChromeOptions()
#         options.add_argument("--disable-infobars")
#         options.add_argument("--disable-extensions")
#         options.add_argument("--start-minimized")
#         options.add_argument("--disable-gpu")  # Disable GPU for smoother performance

#         service = Service(ChromeDriverManager().install())
#         driver = webdriver.Chrome(service=service, options=options)
#         driver.get("https://www.youtube.com")

#         # Wait for the search box to be available before interacting
#         search_box = WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.NAME, 'search_query'))
#         )

#         # Enter the query and press enter
#         search_box.send_keys(query)
#         search_box.send_keys(Keys.RETURN)

#         # Wait until search results are loaded
#         WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.ID, 'video-title'))
#         )

#         # Click the first video
#         first_video = driver.find_elements(By.ID, 'video-title')[0]
#         first_video.click()

#         print(f"Playing {query} on YouTube.")
#         return f"Playing {query} on YouTube."
#     except Exception as e:
#         print(f"Couldn't play song: {str(e)}")
#         return f"Couldn't play song: {str(e)}"

# # Test with a query
# # query = "play arijit on yt"
# # print(playytmusic(query))
