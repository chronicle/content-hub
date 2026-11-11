# language=html
from __future__ import annotations
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta
    content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0"
    name="viewport">
  <meta content="ie=edge" http-equiv="X-UA-Compatible">
  <link
    href="https://fonts.googleapis.com/css?family=Open+Sans:400,400i,700,700i"
    rel="stylesheet">
  <link
    href='https://fonts.googleapis.com/css?family=Source Sans Pro'
    rel='stylesheet'>
  <title>Description</title>
  <style>
      :root {
          --color-link: hsl(217, 89%, 76%);

          --widget-font-style: normal;

          --widget-text-font: 'Source Sans Pro', sans-serif;
          --widget-number-font: 'Open Sans', sans-serif;

          --font-weight-bold: 700;
          --font-weight-semibold: 600;
          --font-weight-regular: 400;

          --font-size-big: 18px;
          --font-size-medium: 16px;

          --default-line-height: 16px;

          --scrollbar-size: 12px;
      }

      strong {
          font-size: var(--font-size-big);
          font-weight: var(--font-weight-bold);
          font-family: var(--widget-text-font);
      }

      .text, p, ol {
          font-size: var(--font-size-medium);
          font-weight: var(--font-weight-regular);
          font-family: var(--widget-text-font);
      }

      code {
          font-size: 10pt;
          color: black;
      }

      .main-table {
          font-family: var(--widget-text-font);
          font-style: var(--widget-font-style);
          font-size: var(--font-size-medium);

          line-height: var(--default-line-height);

          overflow-x: scroll;
      }

      .main-table table {
          font-size: var(--font-size-medium);

          border-collapse: collapse;
          word-break: keep-all;
      }

      .main-table th {
          font-weight: var(--font-weight-semibold);
          line-height: var(--default-line-height);
          font-size: var(--font-size-big);;

          padding: 8px 16px;

          vertical-align: top;
          text-align: center;
          white-space: nowrap;
      }

      .main-table tr {
          font-weight: var(--font-weight-regular);
          font-size: var(--font-size-medium);
      }

      .main-table td {
          padding: 8px 16px;

          vertical-align: top;
      }

      .main-table td:first-child {
          text-align: left;
      }

      table, th, td {
          padding: 8px 16px;

          vertical-align: top;
          text-align: center;
          white-space: nowrap;
      }

      table {
          border-collapse: collapse;
      }

      table td, table th {
          border: 1px solid lightslategray;
      }

      table tr:first-child th {
          border-top: 0;
      }

      table tr:last-child td {
          border-bottom: 0;
      }

      table tr td:first-child,
      table tr th:first-child {
          border-left: 0;
      }

      table tr td:last-child,
      table tr th:last-child {
          border-right: 0;
      }

      .link {
          color: var(--color-link);

          font-family: var(--widget-text-font);
          font-weight: var(--font-weight-regular);
          font-style: var(--widget-font-style);
          font-size: var(--font-size-medium);

          line-height: var(--default-line-height);

          text-decoration-line: underline;
          align-items: center;
      }
  </style>
</head>
<body>
{% if explanation is defined and explanation and exception_instructions is defined and exception_instructions %}
  <p><strong>Finding Explanation</strong></p>
  <span class="text">{{ explanation }}</span>
  <p><strong>Exception Instructions</strong></p>
  <span class="text">{{ exception_instructions }}</span>
{% elif show_description_based_params is defined and show_description_based_params %}
  {% if documentation is defined and documentation %}
    <p><strong>Finding Documentation</strong></p>
    <span class="text">{{ documentation }}</span>
  {% endif %}
  {% if statement is defined and statement %}
    <p><strong>Finding Statement</strong></p>
    <span class="text">{{ statement }}</span>
  {% endif %}
  {% if mitigation is defined and mitigation %}
    <p><strong>Finding Mitigation</p>
    <span class="text">{{ mitigation }}</span>
  {% endif %}
{% else %}
  <p><strong>Finding Description</strong></p>
  {% if description is defined and description %}
    <span class="text">{{ description }}</span>
  {% else %}
    <span class="text">N/A</span>
  {% endif %}
{% endif %}
{% if recommended_steps is defined and recommended_steps %}
  <p><strong>Recommended Steps</strong></p>
  <span class="text">{{ recommended_steps }}</span>
{% else %}
  <p><strong>Next Steps</strong></p>
  {% if next_steps is defined and next_steps %}
    <span class="text">{{ next_steps }}</span>
  {% else %}
    <span class="text">N/A</span>
  {% endif %}
{% endif %}
{% if cvss is defined and cvss %}
  <p><strong>CVSS V3 Information</strong></p>
  {% for name, value in cvss.items() %}
    {% if name and value %}
      <span class="text">{{ name }}: {{ value }}</span>
      <br />
    {% endif %}
  {% endfor %}
{% endif %}
{% if cve is defined and cve %}
  <p><strong>Additional Information</strong></p>
  {% for name, value in cve.items() %}
    {% if name and value %}
      <span class="text">{{ name }}: {{ value }}</span>
      <br />
    {% endif %}
  {% endfor %}
{% endif %}
{% if references is defined and references %}
  <p><strong>Reference Links</strong></p>
  <ul>
  {% for reference in references %}
    <li><a class="link"
           href="{{ reference.uri }}"
           target="_blank">{{ reference.source }}</a></li>
  {% endfor %}
  </ul>
{% endif %}
<div id="main-table"></div>
</body>
</html>"""
