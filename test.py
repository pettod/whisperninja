import rumps

# 💡 Make sure 'my_logo.png' is a small, appropriately sized image 
# (e.g., 18x18 or 22x22 pixels for standard displays).
ICON_PATH = 'whisperninja/assets/logos/whisperninja_white.png' 

class AwesomeApp(rumps.App):
    def __init__(self):
        super(AwesomeApp, self).__init__(
            name="My Awesome App",
            title=None, # Set title to None if you want *only* the icon to appear
            icon=ICON_PATH,
            template=True # 👈 Crucial for proper dark/light mode display
        )
        self.menu = ["Option 1", "Option 2"]

if __name__ == '__main__':
    AwesomeApp().run()