import flet as ft

def main(page: ft.Page):
    try:
        # Test passing string to icon
        s = ft.Segment(
            value="test",
            label=ft.Text("Test"),
            icon="dns"
        )
        sb = ft.SegmentedButton(
            segments=[s]
        )
        page.add(sb)
        print("Successfully created Segment with string icon")
    except Exception as e:
        print(f"Error with string icon: {e}")

    try:
        # Test passing Icon control to icon
        s2 = ft.Segment(
            value="test2",
            label=ft.Text("Test2"),
            icon=ft.Icon(ft.icons.DNS)
        )
        sb2 = ft.SegmentedButton(
            segments=[s2]
        )
        page.add(sb2)
        print("Successfully created Segment with Icon control")
    except Exception as e:
        print(f"Error with Icon control: {e}")

ft.app(target=main)
