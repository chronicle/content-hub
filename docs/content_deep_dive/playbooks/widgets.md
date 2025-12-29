# Deep Dive: Playbook Widgets

Widgets are custom UI components that can be added to a playbook's case overview to display dynamic
information and provide interactive controls. They are a powerful way to visualize data, present
findings, and enable analysts to take action directly from the case.

For more detailed information on playbook widgets in Google Security Operations, you can refer to
the official documentation:
[Google Cloud: Using predefined widgets in playbook views](https://docs.cloud.google.com/chronicle/docs/soar/respond/working-with-playbooks/using-predefined-widgets-in-playbook-views)

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

Each widget is defined by two files in the `widgets/` directory: an HTML file for the structure and
a YAML file for the configuration.

### 1. HTML File (`<widget_name>.html`)

The HTML file defines the structure and layout of the widget. It is standard HTML, but with the
ability to include placeholders that are dynamically replaced with data from the playbook.

### 2. YAML File (`<widget_name>.yaml`)

The YAML file configures the widget and links it to the playbook's data. It defines:

- The **name** and **description** of the widget.
- The **data sources** that the widget will use (e.g., playbook steps, case data).
- The **version** and other metadata of the widget.

## Predefined Widgets

Google SecOps provides a set of predefined widgets that can be used out-of-the-box to display common
types of information. These include:

* **Table Widget:** Displays data in a tabular format.
* **JSON Widget:** Renders a JSON object in a collapsible tree view.
* **HTML Widget:** Displays raw HTML content.
* **Markdown Widget:** Renders Markdown content.

These predefined widgets can be customized to display the specific data you need, without requiring
you to write any HTML.

## Custom Widgets

For more complex visualizations or interactions, you can create custom widgets using HTML, CSS, and
JavaScript. This allows for a high degree of flexibility in how you present information and interact
with the user.
