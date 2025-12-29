# Widgets

Widgets are custom UI components that can be added to a playbook's case overview to display dynamic
information and provide interactive controls. They are a powerful way to visualize data, present
findings, and enable analysts to take action directly from the case.

Each widget is defined by two files in the `widgets/` directory: an HTML file for the structure and
a YAML file for the configuration.

## What is a Widget?

A widget is essentially a small web application that runs within the context of a playbook case. It
can:

* **Display data:** Visualize data from the playbook, such as enrichment results, risk scores, or
  entity relationships.
* **Provide interactivity:** Include buttons, forms, and other interactive elements that allow
  analysts to trigger actions or provide input to the playbook.
* **Integrate with external services:** Fetch and display information from external tools or APIs in
  real-time.

Widgets are crucial for creating a rich and interactive experience for the analyst, transforming the
case from a static report into a dynamic workspace.

## Widget Structure

### 1. HTML File (`<widget_name>.html`)

The HTML file defines the structure and layout of the widget. It is standard HTML, but with the
ability to include placeholders that are dynamically replaced with data from the playbook.

### 2. YAML File (`<widget_name>.yaml`)

The YAML file configures the widget and links it to the playbook's data.
