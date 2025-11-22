import flet as ft

try:
    print("Attempting to create Segment with string icon...")
    # Test passing string to icon
    s = ft.Segment(
        value="test",
        label=ft.Text("Test"),
        icon="dns"
    )
    print("Successfully created Segment with string icon")
except Exception as e:
    print(f"Error with string icon: {e}")

try:
    print("Attempting to create Segment with Icon control...")
    # Test passing Icon control to icon
    s2 = ft.Segment(
        value="test2",
        label=ft.Text("Test2"),
        icon=ft.Icon(ft.icons.DNS)
    )
    print("Successfully created Segment with Icon control")
except Exception as e:
    print(f"Error with Icon control: {e}")
