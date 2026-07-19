##    **What is Parsing and why is it important?**

   	In Chronicle, configuration based normalizers are used to handle the parsing of event data in a consistent fashion. This leverages the filter portion of the Logstash configuration, however, not all Logstash capabilities are supported within Chronicle's parser language. Additionally, there are a number of features, such as statedump, that are extensions of capabilities. Parser translates raw event messages into Chronicle's standardized UDM schema.

## **Building a Parser**

To build an efficient and accurate parser, it is best to follow a structured, phased approach.

Below are the core steps which need to be followed in  the same order for  developing a parser, which we will break down in detail below. 

1. **Initialize Fields:** Set fields to empty (`""`)at the beginning of the parser to ensure clean conditional checks later before mapping.  
2. **Data Extraction:** Identify the log format and select the appropriate filter (GROK, JSON, XML, KV, or CSV) to pull the raw data into fields.  
3. **Data Transformation and Mapping to UDM:** Plan how to map the extracted data into the Unified Data Model (UDM) schema, grouping related fields and following a strict hierarchical order.

   ### **1\. Initializing Fields**

   Before extracting any data, start by initializing the fields you plan to use to empty values (`""`).  
   **Why it is important:** 

During the mapping phase, you will frequently write conditional statements to check if a piece of data exists before attempting to map it (e.g., `if [source_ip] != "" { ... }`). If a field is not initialized and the extraction phase fails to populate it, referencing that missing field later can cause the parser to fail or produce unintended results. Initializing establishes a clean baseline.

### **2\. Data Extraction**

Logs are typically ingested in one of several standard formats, most notably JSON, SYSLOG, KV (Key-Value), XML, and CSV. Following variable initialization, an appropriate filter should be applied to extract the data . Selecting the correct extraction filter is critical for parsing efficiency and overall system performance.

####      **Handling Hybrid Log Formats**

Frequently, logs arrive in a hybrid format, combining a standard unstructured header with a structured payload (e.g., SYSLOG \+ JSON, or SYSLOG \+ KV). In these scenarios, a single filter is insufficient. The parser must isolate the distinct data components and apply the appropriate filters sequentially.

**Example: Parsing SYSLOG \+ KV** 

If a log contains a standard SYSLOG header followed by a KV payload, you must utilize a multi-step extraction strategy:

* **Initial Extraction (`grok`):** First, apply a `grok` filter to parse the unstructured SYSLOG header (extracting metadata such as the timestamp and host). Within this same Grok pattern, capture the entire remaining KV message into a single, dedicated intermediate variable (e.g., `%{GREEDYDATA:kv_data}`).  
* **Secondary Extraction (`kv`):** Next, apply the `kv` filter, configuring it to target specifically the `kv_data` variable rather than the entire raw log. This efficiently parses the remaining key-value pairs into individual fields without requiring complex, computationally heavy regular expressions.

   Here is how to handle each of the standard log formats:

####    **GROK**

Using GROK, you can create predefined patterns in addition to regular expressions to match log messages and extract values into tokens from the log message. GROK data extraction requires that field labels are defined as part of the data extraction process.

GROK patterns can be found [here](https://github.com/elastic/logstash/blob/v1.4.2/patterns/grok-patterns).

##### **GROK Best Practices**

To maintain performance and stability within your parsers, adhere to the following principles when writing GROK filters:

1. **Intent-Based Naming Conventions:** All GROK variable names should clearly state their intent (e.g., use `source_ip` or `target_port` rather than vague names like `ip1` or `val2`).  
2. **Initialize and Overwrite:** All GROK variables must be initialized (set to `""`) at the top of the parser. Furthermore, these variables must be explicitly declared in the `overwrite` array of the `grok` filter block. This prevents flakiness and ensures the variables are explicitly overwritten with the newly fetched values from the GROK extraction.  
3. **Leverage Predefined Patterns:** Always use existing GROK variables (such as `%{SPACE}`, `%{WORD}`, or `%{IP}`) whenever possible, rather than writing custom regular expressions to handle spaces or common data types. This improves parsing efficiency and readability.

#####      **Types of GROK patterns**

When building a GROK filter, there are two types of patterns you will use to extract data: **Custom Regular Expressions** (which are necessary for unique or proprietary log formats) and **Predefined GROK Patterns**.

1. ###### **Predefined GROK Patterns**

   Predefined GROK patterns are built-in, pre-tested regular expressions bundled within the Logstash engine. They act as shorthand aliases for complex regex strings. Instead of manually writing a long, error-prone regular expression to identify an IPv4 or IPv6 address, you can simply call the %{IP} pattern.  
* **Syntax:** %{pattern:token}  
* **Examples:** %{IP:hostip}, %{NUMBER:event\_id}, %{MAC:principal\_mac}  
  **Why Use Predefined Patterns?**  
  **Readability:** A pattern like `%{IP:source_ip}` is instantly understandable to any engineer reading the code, whereas the raw regex equivalent `(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)` is visually dense and difficult to parse.  
  **Efficiency:** Chronicle and Logstash are optimized to process these standard patterns rapidly, making your parser run more efficiently at scale.

2. ######  **Custom Regular Expressions in GROK**

         While predefined GROK patterns (like %{IP} or %{INT}) are highly efficient for standard data types, log structures are rarely perfect. You will frequently encounter custom application logs, proprietary transaction IDs, or unusual delimiters (like brackets, pipes, or carets) where predefined patterns fall short or extract too much data.  
         In these scenarios, you must embed **Custom Regular Expressions** directly into your GROK match statement.  
     
   

   Custom regex in GROK utilizes Named Capture Groups.   
   **The standard format is:** (?P\<variable\_name\>regular\_expression)  
   **Example :** (?P\<user\>\[a-zA-Z\\\\-\]+)

   **When to Use Custom Expressions**

   You should write a custom expression when:  
1. **Data is wrapped in unusual delimiters:** Extracting admin from User:\<admin\>.  
2. **Predefined patterns are too greedy:** %{WORD} stops at hyphens. If a username is john-doe, %{WORD} only captures john. A custom regex like (?P\<user\>\[a-zA-Z\\\\-\]+) captures the whole string.  
3. **Validating strict formats:** Ensuring a captured ID strictly matches a specific corporate format (e.g., exactly 3 letters followed by 4 digits).

#####      **Chronicle Constraints**

**The Double Backslash Rule:**

      Because Logstash and Chronicle's parser engine interpret string literals before passing them to the regex engine, you must "escape the escape character." This means any regex token that normally uses a single backslash (\\) requires a **double backslash (\\\\)** in Chronicle.

* Standard Regex Space: \\s \-\> **Chronicle Regex:** \\\\s  
* Standard Regex Digit: \\d \-\> **Chronicle Regex:** \\\\d  
* Standard Literal Period: \\. \-\> **Chronicle Regex:** \\\\.  
* Standard Literal Bracket: \\\[ \-\> **Chronicle Regex:** \\\\\[

| Regex | Data |
| :---- | :---- |
| \\\\s | Space |
| \\\\S | Not space |
| \\\\d | Digit |
| \\\\D | Not digit |
| \\\\w | Word |
| \\\\W | Not word |

           




##### 

##### 

##### 

##### **Example**

**The Scenario:** We are parsing a **hybrid log format** (Syslog \+ KV) generated by a custom VPN gateway.

* The first half of the log is an unstructured Syslog header containing unusual delimiters (brackets and angle brackets) that require **Custom Regular Expressions**.  
* The second half of the log is a structured Key-Value (KV) payload.  
* We must use **Predefined Patterns** where possible, apply **intent-based naming**, **initialize** our variables, and use the **overwrite** function to prevent flakiness.  
  **The Raw Log Message**


```
Oct 27 15:42:11 sec-gateway-01 vpn_module: User [jdoe-admin] ,status=<FAILED>. src_ip=192.168.1.50 dst_port=443 action=block
```


  **The Parser Configuration**


```
# ===================================================================
# PHASE 1: Initialization
# Initialize all GROK and intermediate variables to empty strings.
# This ensures clean conditional checks later and prevents data bleeding.
# ====================================================================
mutate {
  replace => {
    "syslog_timestamp" => ""
    "device_name" => ""
    "module_name" => ""
    "target_username" => ""
    "auth_status" => ""
    "kv_payload" => ""
  }
}

#====================================================================
# PHASE 2: GROK Extraction (Handling the Unstructured Header)
# We use GROK to parse the Syslog header and isolate the KV payload.
#====================================================================
grok {
  match => {
    "message" => [
      # 1. Predefined Patterns for standard fields:
      "%{SYSLOGTIMESTAMP:syslog_timestamp} %{HOST:device_name} %{WORD:module_name}: User \\[(?P<target_username>[a-zA-Z0-9\\-]+)\\] ",status=<(?P<auth_status>[A-Z]+)>\\.%{SPACE}%{GREEDYDATA:kv_payload}"]
  }
  # Overwrite explicitly prevents flakiness by replacing the initialized null/empty 
  # values with the newly fetched data from the GROK match.
  overwrite => [
    "syslog_timestamp", "device_name", "module_name", "target_username", "auth_status", "kv_payload"
  ]
  on_error => "grok_failed"
}

#====================================================================
# PHASE 3: KV Extraction (Handling the Structured Payload)
# Now that GROK has isolated the KV portion into the 'kv_payload' variable, 
# we apply the highly efficient KV filter to that specific field.
# ===================================================================
if [kv_payload] != "" {
  kv {
    source => "kv_payload"
    field_split => " "
    value_split => "="
    on_error => "invalid_kv"
  }
}

```




#### **JSON**

When a log is formatted in JSON (JavaScript Object Notation), the json filter is the most efficient method for extraction. Chronicle provides specific parameters and loops to handle these data sets safely.

##### **JSON Extraction Syntax**

The standard JSON filter automatically parses top-level key-value pairs into intermediate variables.

```
json {
  source => "message"
}
```

If your raw log is {"username": "admin", "action": "login"}, this filter automatically creates two variables: username and action, which you can then map to UDM.

##### **Manipulating JSON Arrays**

Standard JSON extraction has arrays (e.g., {"ips": \["1.2.3.4", "10.0.0.1"\]}). To make array elements accessible, you must append the array\_function \=\> "split\_columns" parameter to your filter.

```
json {
  source => "message"
  array_function => "split_columns"
  on_error => "not_json"
}
```

The split\_columns function makes elements of an array accessible through their index. So if you have an array that looks like the following { "ips" : \["1.2.3.4","1.2.3.5"\] .. }

you will be able to access the two values through ips.0 and ips.1

If you have nested arrays or multiple arrays it will unnest all of them recursively.

Let's take a nested array example.

```
{ "devices" : \[ "ips" : \[ "1.2.3.4"] ] }
```

In this case you will access the ip through devices.0.ips.0

##### **Handling Fluctuating Nested JSON Objects**

Because log payloads fluctuate, if you have an object inside a JSON that varies from log to log, you must not map it directly to UDM or use it in direct conditional logic.  
Attempting to directly reference a deeply nested object (e.g., network.source.hostname) that happens to be missing in the current log will cause parsing issues.

**The Solution:** First, extract the JSON object into a safe intermediate variable using a replace (which fails gracefully). Then, perform a null-check on that intermediate variable before mapping it to your final UDM schema.

**❌ The Unsafe Way: Direct Conditional Logic**

If the `network` or `source` object doesn't exist in the current log, evaluating this `if` statement or attempting the direct mapping will crash the parser:

```
# DANGEROUS: If network/source is missing, the parser fails here.
if [network][source][hostname] != "" {
    replace => {
        "source_hostname" => "%{network.source.hostname}"
    }
    on_error => "source_hostname_not_found"
}
```

**The Safe Way: Intermediate Extraction & Null Check**

```
# Step 1: Safely extract the nested object to an intermediate variable.
# Using replace with on_error ensures that if the nested path is missing, 
# it fails gracefully without crashing the pipeline, while tagging the error.
mutate {
    replace => {
        "source_hostname" => "%{network.source.hostname}"
    }
    on_error => "network_source_hostname_not_found"
}
# Step 2: Perform conditional logic on the SAFE intermediate variable and Safely map to the final UDM schema.
    # Using merge handles array populations safely, and adding a second 
    # on_error protects against type-mismatches during UDM assignment.␋if [source_hostname] != "" {
    mutate {
        replace => {
            "event.idm.read_only_udm.principal.hostname" => "%{source_hostname}"
        }
        on_error => "invalid_hostname_mapping"
    }
}
```

##### **Iteration over JSON Array**

We can create an iterable JSON array by splitting.

```
 json {
    source => "message"
    array_function => "split_columns"
    on_error => "invalid_json"
  }
```

Example log:

```
entries: < data: "{\"businessPhones\":[\"(123) 234-2320\",\"(123) 234-2321\"]}",
```

Use the "for in" construct to iterate over phone numbers:

```
 for index,phoneNumber in businessPhones {
      mutate {
        merge => {
          "entity.user.phone_numbers" => "phoneNumber"
        }
        on_error => "invalid_phone_number"
      }
    }
```

Note \- 0-based indexing.

UDM output

```
entity: {
          user: {
            phone_numbers: "(123) 234-2320"
            phone_numbers: "(123) 234-2321"
           }
        }
```

We also support nested for loop. See the sample below:

```
for msgPart in msgParts {
  for url in msgPart.urls {
      mutate {
        replace => {
          "about" => ""
        }
      }
      mutate {
        rename => {
          "url.url" => "about.url"
        }
      }
      mutate {
        merge => {
          "event.idm.read_only_udm.about" => "about"
        }
        on_error => "no_about"
      }
  }
}
```

#### **XML**

      When processing logs formatted in XML (eXtensible Markup Language), such as Windows Event Logs, Chronicle utilizes the `xml` filter. Data extraction is achieved by defining **XPath** expressions that map specific XML nodes directly to intermediate variables.

##### **Basic XML Extraction**

The standard `xml` filter requires you to specify the `source` field containing the XML payload (typically `message`) and a dictionary of `xpath` mappings.

```

xml {
  source => "message"
  xpath => {
    "/Event/System/EventID" => "event_id"
    "/Event/System/Computer" => "hostname"
  }
}

```

*In this example, the parser looks down the XML tree into `<Event><System><EventID>`, extracts the value, and stores it in the `event_id` variable.*

##### **Iterating Over XML Elements**

If your XML payload contains repeating elements (like a list of hosts or multiple IP addresses), you cannot use a static XPath. Instead, you must use a `for` loop utilizing the `xml()` function to iterate through the nodes.

**CRITICAL DIFFERENCE:** 

Unlike JSON arrays which use 0-based indexing, **XML loop indexing in Chronicle starts at 1\.**

**The Scenario:** You have a log with multiple hosts inside a `<HOST_LIST>` node.

For example if the sample looks like this:

```
message - <Event><HOST_LIST><HOST><ID>iD1</ID><IP>iP1</IP></HOST><HOST><ID>iD2</ID><IP>iP2</IP></HOST></HOST_LIST></Event>
```

If we want to iterate over the above sample log then use the following:

**The Loop Configuration:** Notice how the `%{index}` variable is injected dynamically into the XPath to target the correct node during each iteration.

```
for index,event in xml(message,/Event/HOST_LIST/HOST){
   xml {
    source => "message"
    xpath => {
      "/Event/HOST_LIST/HOST[%{index}]/ID" => "IDs"
      "/Event/HOST_LIST/HOST[%{index}]/IP" => "IPs"
    }
  }
}
```

##### 

##### 

##### 

##### **Nested XML Iteration**

Chronicle also supports nested loops for highly complex XML structures, such as a list of hosts where each host contains its own list of file hashes.

To achieve this, you nest the loops and use the outer loop's index (`%{index}`) alongside the inner loop

See the sample below:

```
entries: <
    message: "<Event><HOST_LIST><HOST><ID>id1</ID><IP>ip1</IP><Hashes><Hash>hash1</Hash><Hash>hash2</Hash></Hashes></HOST><HOST><ID>id2</ID><IP>ip2</IP><Hashes><Hash>hash1</Hash><Hash>hash2</Hash></Hashes></HOST></HOST_LIST></Event>"
```

```
for index, event in xml(message, /Event/HOST_LIST/HOST){
    xml {
      source => "message"
      xpath => {
        "/Event/HOST_LIST/HOST[%{index}]/ID" => "IDs"
      }
    }
    for i, hash in xml(message, /Event/HOST_LIST/HOST[%{index}]/Hashes/Hash) {
      xml {
        source => "message"
        xpath => {
          "/Event/HOST_LIST/HOST[%{index}]/Hashes/Hash[%{i}]" => "data"
        }
      }
    }
  }
```

#### **KV** 

Many security appliances (such as firewalls and web proxies) generate logs in a structured Key-Value format (e.g., src\_ip=192.168.1.1 action=block). The kv filter is highly optimized to process this format, making it significantly faster and less resource-intensive than writing custom GROK regular expressions.

To extract data correctly, you must tell the parser exactly which characters separate the pairs, and which characters separate the keys from the values.

##### **KV Configuration Options**

The kv filter supports several parameters to handle messy or complex log strings cleanly:

* `source`: The field containing the data to be parsed (typically `"message"` or an intermediate variable extracted earlier).  
* `field_split`: Identifies the delimiter that separates different key-value pairs from one another (e.g., a space, a comma, or an ampersand `&` in a URL query string).  
* `value_split`: Identifies the delimiter that links the key to its corresponding value (most commonly `=` or `:`).  
* `trim_value`: Removes extraneous surrounding characters from the extracted value. For example, if a log outputs `user="admin"`, setting `trim_value => "\""` ensures the variable stores `admin` instead of  `"admin"`.  
* `whitespace`: Dictates how surrounding whitespace is handled. The default is `lenient` (which ignores unnecessary spaces). If you have a specific use case where spaces must be strictly evaluated as part of the key or value, set this to `"strict"`.

##### **Standard KV Syntax Example**

Here is a standard configuration that strips quotation marks and uses standard delimiters:

**Code snippet**

```
kv {
  source => "message"
  field_split => "|"
  value_split => ":"
  whitespace => "strict"
  trim_value => "\""
}
```

##### **Handling Special Characters (Unescaping)**

Sometimes logs use special control characters—such as tabs (\\t), newlines (\\n), or carriage returns (\\r)—as their delimiters.

If your field\_split or value\_split relies on one of these special symbols, you must explicitly tell the filter to unescape them by setting the corresponding boolean option to true.

For example if the sample looks like this:

```
key1=value1\tkey2=value2
```

The Configuration: To parse this correctly, define \\\\t as the split character and enable unescape\_field\_split.

**Code snippet**

```
kv {
  source => "message"
  field_split => "\\t"
  value_split => "="
  unescape_field_split => true
}
```

*Note: A similar parameter, unescape\_value\_split \=\> true, is available if the special character sits between the key and the value.*

#### **CSV**

When ingesting delimited log formats (such as comma-separated, tab-separated, or pipe-separated values), the payload does not contain explicit field names (keys). Instead, the data is entirely positional. The `csv` filter is designed to slice this payload into variables based on a defined delimiter.

##### **Default Positional Extraction**

Because there are no keys in the raw log, the `csv` filter automatically assigns default field names to the extracted values. By default, these fields are prefixed with the word `column` and increment numerically starting at 1 (e.g., `column1`, `column2`, `column3`).

##### **Basic CSV Configuration**

The standard `csv` filter requires you to define the `source` field and the `separator` character that divides the values.

Code snippet

```
csv {
  source => "message"
  separator => ","
}
```

##### **Handling Special Character Delimiters (`unescape_separator`)**

Frequently, delimited logs are separated by control characters rather than standard punctuation, with horizontal tabs (`\t`) being the most common.

If your file is tab-delimited, you must set the separator to `\\t` and explicitly tell the filter to unescape it by enabling the `unescape_separator` boolean.

**Log**

```
event_id=4624\tlog_name=Security\ttarget_user=admin\tdomain=LOCAL
```

**Code snippet**

```
csv {
  source => "message"
  separator => "\\t"
  unescape_separator => true
}
```

**Default Extracted Variables:** Because CSV is purely positional and no custom column names were provided, the parser automatically assigns the `columnX` naming convention:

* `column1` \= `2026-07-13 12:30:15`  
* `column2` \= `10.0.0.5`  
* `column3` \= `443`  
* `column4` \= `192.168.2.20`  
* `column5` \= `53210`  
* `column6` \= `TCP`  
* `column7` \= `BLOCK`

##### **Handling Malformed Quotation Marks (`lazy_quotes`)**

In improperly formatted CSV logs, you may encounter edge cases with quotation marks that break standard CSV parsing rules. This includes scenarios where:

* A quoted field exists inside a non-quoted field.  
* A non-doubly quoted field exists inside a quoted field.

To prevent the parser from failing when it encounters these syntax anomalies, enable the `lazy_quotes` parameter. This instructs the filter to process the quotes leniently rather than strictly enforcing standard CSV quote-escaping rules.

**Log**

```
102\t"Internal "Critical" Server"\t192.168.1.100\t"Failed login"
```

**Code snippet**

```
csv {
  source => "message"
  separator => "\\t"
  unescape_separator => true
  lazy_quotes => true
}
```

**Default Extracted Variables:** Without `lazy_quotes => true`, the unescaped internal quotes around `"Critical"` would cause the parser to fail. With it enabled, the strings extract cleanly:

* `column1` \= `102`  
* `column2` \= `Internal "Critical" Server`  
* `column3` \= `192.168.1.100`  
* `column4` \= `Failed login`

### **3\. Data Transformation and Mapping to UDM**

#### **Mutate**

Use the mutate filter plugin to transform and consolidate data into a single block or to break the data into separate mutate blocks. When using a single block for the mutate functions, be aware that the mutations are executed in the order described in the Logstash mutate plugin documentation.

#####       **The "One Operation Per Mutate" Rule**

In Chronicle parser development, it is highly advised to place only ONE operation type inside each `mutate` block.

**Why this is necessary:** When troubleshooting or implementing defensive parsing with `on_error` tags, tracking down failures becomes incredibly difficult if a block has multiple transformations.

* **Error Ambiguity:** If a `mutate` block contains two or three separate operations (e.g., a `replace` and a `convert`) and a parsing error occurs, the `on_error` flag will catch the exception but cannot tell you *which* specific operation failed.  
* **Isolated Error Tracking:** By isolating each filter to its own individual `mutate` block, you isolate the error handling. If a single block fails, your `on_error` tag lets you pin down the exact field and operation that caused the failure without guessing, keeping the rest of your parsing logic running smoothly.


      **Code Example: The Wrong vs. Right Way**

      **The WRONG Way (Consolidated Block):** *If an error occurs here, it is impossible to determine whether the `replace` or the `convert` triggered the exception.*

Code snippet

```
mutate {
  replace => { "temp_port" => "%{src_port}" }
  convert => { "temp_port" => "integer" }
  on_error => "port_transformation_failed"
}
```

**The RIGHT Way (Isolated Blocks):**

 *Each operation handles its own tracking, allowing for exact error diagnosis.*

Code snippet

```
# 1. Isolate the string assignment
mutate {
  replace => {
    "temp_port" => "%{src_port}"
  }
  on_error => "port_assignment_failed"
}

# 2. Isolate the type conversion
mutate {
  convert => {
    "temp_port" => "integer"
  }
  on_error => "port_type_conversion_failed"
}
```

#### **Convert**

The `convert` function transforms data from its raw extracted format into the specific data type required by the target schema.

While the modern Unified Data Model (UDM) allows for the handling of most fields as standard strings—including IP addresses—proper data type conversion remains essential.

#####       **Supported Data Types**

Chronicle's parser language supports a wide range of standard and specialized data types for conversion:

* **boolean**: Transforms values to true/false states.  
* **bytes**: Handles raw byte sequences.  
* **bytestohex**: Converts raw byte sequences into a hexadecimal string representation.  
* **bytestip**: Converts a raw byte sequence directly into a valid network IP address.  
* **float**: Converts numbers into floating-point decimals.  
* **hash**: Standardizes cryptographic hashes.  
* **hextoascii**: Converts hex-encoded strings back into readable ASCII characters.  
* **hextodec**: Translates hexadecimal strings directly into their base-10 decimal equivalents (e.g., converting a hex event ID or process ID).  
* **integer / uinteger**: Converts strings to signed or unsigned integers (frequently used for ports, status codes, and event IDs).  
* **ipaddress**: Validates and converts into network-layer IP addresses.  
* **macaddress**: Converts and normalizes physical hardware addresses.  
* **millitonanos**: Converts timestamps or durations from milliseconds to nanoseconds.  
* **millitosecs**: Converts timestamps or durations from milliseconds to seconds.  
* **parseduseragent**: Parses complex browser/system user-agent strings into structured fields.  
* **string**: Explicitly casts values (like integers or booleans) into a standard string format.

  Example


```
mutate {
  convert => {
    # convert id (in HEX format) to decimal
    "id" => "hextodec"
  }
  on_error => "invalid_conversion"
}
```


  


  


#### **Gsub**

         Match a regular expression against a field value and replace all matches with a                   replacement string. This applies only to string fields.

##### **Syntax**

The `gsub` configuration takes an array consisting of exactly **three elements per substitution**. For every modification you want to make, you must add the elements in the following precise order:

1. **Field Name:** The target string field to be modified.  
2. **Regular Expression:** The pattern or string to search for.  
3. **Replacement String:** The string that will replace the matches.

   ##### **Regular Expression & Escaping Rules**

* **Simple Strings:** You can use simple strings for matching most of the time, provided they do not contain characters with special meanings in regular expressions (such as brackets `[` or `]`).  
* **Escaping Special Characters:** If you need special characters to be interpreted literally, you must "escape" them by preceding each character with a single backslash (`\`).  
* **The Backslash Exception:** To match a literal backslash, both the backslash itself and its escape character must be escaped. Therefore, to refer to a single literal backslash in the configuration, you must use **four backslashes (`\\\\`)**.  
  


```
mutate {
  gsub => [
    "fieldname1", "cat", "dog",
    # replace all forward slashes with underscore
    "fieldname2", "/", "_",
    # replace backslashes, question marks, hashes, and minuses
    # with a dot "."
    "fieldname3", "[\\\\?#-]", "."
  ]
}
```


####  **Lowercase**

The lowercase function is used to transform a value into an lowercase value.

##### **Syntax**

```
mutate {
  lowercase => [ "token" ]
}
```

##### **Example**

```
mutate {
  lowercase => [ "protocol" ]
}
```

#### **Uppercase** 

The uppercase function is used to transform a value into an uppercase value.

##### **Syntax**

```
mutate {
  uppercase => [ "token" ]
}
```

##### **Example**

```
mutate {
  uppercase => [ "protocol" ]
}
```

#### 

#### 

#### **Merge**

The `merge` function is used to join multiple fields together. It is primarily used for handling repeated fields (such as lists of IP addresses) and for generating normalized output structures to produce multiple events from a single log line.

##### **Syntax**

The `merge` configuration inside the mutate block where the value of the source token is combined into the destination token.

```
mutate {
  merge => {
    "destinationToken" => "addedToken"
  }
}
```

##### **Examples**

**Example 1: Handling Repeated Fields**

Repeated fields, such as array-based IP address fields, require the `merge` function to properly assign and append multiple values to a token.

```
mutate {
  merge => {
    "event.idm.read_only_udm.target.ip" => "dstAddr"
  }
  on_error => "dstAddr_invalid"
}
```

#### 

#### 

**Example 2: Merge Function Example \- Output**

```
mutate {
  merge => {
    "@output" => "event"
  }
}
```

#### **Rename**

The `rename` function changes the name of an existing token and assigns its value to a new token. Use this function when a tokenized value can be mapped directly to a schema-defined token.

> ##### ⚠️ **Critical Behaviors:**

> * **Destructive Action:** The rename process **destroys the original token**. Once completed, the original token no longer exists in the event pipeline.  
> * **Type Requirement:** The original token and the new token must share the exact same data type prior to performing the transformation.  
> * **Not Fail-Safe:** The rename function is not structurally fail-safe. Even if you define an on\_error catch block or routing condition, it will not catch failures triggered by the rename process (e.g., if the source token is missing or malformed).

##### **Syntax**

```
mutate {
  rename => {
    "originalToken" => "newToken"
  }
}
```

##### **Example**

```
mutate {
  rename => {
    "proto" => "event.idm.read_only_udm.network.application_protocol"
  }
}
```

#### **Replace**

The replace function assigns a value to a token. The assignment can be based on  
constants, existing field values or a combination of values. The replace function can also be  
used to define a token declaration. This function can only be used for string values.

##### **Replace Syntax \- Assign a Constant**

```
mutate {
  replace => {
    "token" => "newConstantValue"
  }
}
```

##### **Replace Syntax \- Assign a Variable Value**

```
mutate {
  replace => {
    "token" => "%{otherTokenValue}"
  }
}
```

##### **Replace Function Example \- Assign a Constant**

```
mutate {
  replace => {
    "event.webproxy.action" => "ALLOWED"
  }
}
```

##### **Replace Function Example \- Assign a Variable Value**

```
mutate {
  replace => {
    "shost" => "%{dhost}"
  }
}
```

#### **remove\_field**

The remove\_field function destroys a token. The name of the token to be destroyed can be either static or dynamic using existing token values. No action is performed if the token doesn't exist.

##### **RemoveField Syntax \- Remove a static token**

```
mutate {
  remove_field => [ "token" ]
}
```

##### **RemoveField Syntax \- Remove a dynamic token**

```
mutate {
  remove_field => [ "%{someTokenValue}" ]
}
```

##### **RemoveField Function Example \- Remove a static token**

```
mutate {
  remove_field => [ "event.webproxy.protocol" ]
}
```

##### **RemoveField Function Example \- Remove a dynamic token**

```
mutate {
  remove_field => [ "network.%{application_protocol}" ]
}
```

#### **Copy** 

The `copy` function performs a deep copy of a source token's value into a destination token.

💡 **Core Difference from `rename`:** Unlike `rename`, the `copy` function preserves the original source token in the pipeline. Because it is a true **deep copy**, any subsequent mutations to the destination token will have no effect on the source token (and vice-versa).

##### **Operational Rules**

* **Prerequisite:** The source token **must exist** in the pipeline before the `copy` function is executed.  
* No Type Restrictions: There is no restriction on type of value that can be copied.   
* **Destination Behavior:** If the destination token does not exist, a new token is dynamically created. If it already exists, its old value is completely overwritten.

##### **Syntax**

```
mutate {
  copy => {
    "destinationToken" => "sourceToken"
  }
}
```

##### **Example**

```
mutate {
  copy => {
    "event.webproxy.client.ip" => "src_ip"
  }
}
```

#### **Split**

The `split` function terminates a single string value by breaking it apart into an iterable array based on a designated delimiter string.

##### **Syntax**

Unlike key-value map structures, the `split` configuration block takes an explicit set of three configuration parameters:

* **`source`:** The name of the existing string field you want to split.  
* **`separator`:** The character or string delimiter used to split the source text.  
* **`target`:** The destination field where the newly created array will be stored.

```
mutate {
  split => {
    source    => "src_field"
    separator => ","
    target    => "target_field"
  }
}
```

##### **Example**

```
mutate {
  split => {
    source    => "csv_data"
    separator => "|"
    target    => "parsed_array"
  }
}
```

#### **Date**

The date filter parses dates and timestamps from log extractions to establish a normalized timeline. All log parser configurations require a properly normalized date value. By default, the date filter's output target is the @timestamp field, which serves as the final, official event time for all processed logs.

#####  **System-Supplied Timestamps**

The processing pipeline automatically exposes up to three system metadata timestamps:

* **@createTimestamp**: Always available. Represents the exact time the pipeline received the logs.  
* **@timestamp**: Optional/Variable. Contains the timestamp provided by collection sources (e.g., Splunk or PCAP), if present.  
* **@collectionTimestamp**: Optional. Represents the time the log forwarder collected the entry. *Note: This may be missing for logs ingested via out-of-band processors.*

> 💡 **Best Practice:** Always extract the event time directly from the raw log message text using the date filter. If the log completely lacks a timestamp, use the rename function to map @createTimestamp to @timestamp as a fallback.

##### **Supported Pre-Defined Formats**

Instead of explicit pattern strings, you can pass these pre-defined format identifiers directly into the match configuration:

* ISO8601  
* RFC3339   
* UNIX (Seconds since epoch)  
* UNIX\_MS (Milliseconds since epoch)

##### **Custom Date Format Tokens**

When defining custom layout strings, use the following syntax patterns:

| Category | Token | Description | Example |
| :---- | :---- | :---- | :---- |
| **Year** | yyyy | Full four-digit year | 2015 |
|  | yy | Two-digit year | 15 (for 2015\) |
| **Month** | M | Minimal-digit numeric month | 1 (January), 12 |
|  | MM | Two-digit zero-padded month | 01 (January), 12 |
|  | MMM | Abbreviated month text | Jan |
|  | MMMM | Full month text | January |
| **Day** | d | Minimal-digit day of the month | 1 |
|  | dd | Two-digit zero-padded day | 01 |
| **Hour** | H | Minimal-digit hour (24-hour clock) | 0 (Midnight) |
|  | HH | Two-digit zero-padded hour (24-hour) | 00 (Midnight) |
| **Minutes** | m | Minimal-digit minutes | 0 |
|  | mm | Two-digit zero-padded minutes | 00 |
| **Seconds** | s | Minimal-digit seconds | 0 |
|  | ss | Two-digit zero-padded seconds | 00 |
| **Sub-Seconds** | S | Tenths of a second | 1 |
|  | SS | Hundredths of a second | 12 |
|  | SSS | Milliseconds | 123 |
| **Time Zone** | Z | Numerical time zone offset | \-0700 |
|  | ZZ | Coloned time zone offset | \-07:00 |
|  | ZZZ | Three-letter abbreviation (Parse only)\* | MST |
| **AM / PM** | A or a | Case-dependent meridian indicator | AM / pm |

*\*Note on ZZZ: This only parses the zone string text but does not calculate a numerical offset adjustment. To apply structural hour offsets via textual time zones, incorporate the standard timezone.include configuration file and use Z for parsing.*

##### **Configuration Syntax & Examples**

##### **Standard Matching**

Matches a single field against a specified pattern layout.

```
date {
  match => ["when", "yyyy-MM-dd HH:mm:ss"]
}
```

**Timezone Specification**  
Explicitly declares the source timezone context when the log string lacks explicit offset data.

```
date {
  match    => ["logtime", "yyyy-MM-dd HH:mm:ss"]
  timezone => "America/New_York"
}
```

### 

**Multiple Date Formats (Fallback Array)**  
Evaluates a field against multiple potential formats in sequential order until a successful match is hit.

```
date {
  match => ["ts", "yyyy-MM-dd HH:mm:ss", "RFC3339", "UNIX", "ISO8601", "UNIX_MS"]
}
```

### 

##### **The rebase Option (Handling Missing Years)**

Used for log formats (like standard Syslog) that omit the year value. Setting rebase \=\> true dynamically contextualizes the event year relative to current ingestion time.

> 🛑 **Critical Engineering Rules:**

> 1. **Mandatory Rule for Missing Years:** If the log timestamp completely lacks a year value (e.g., `Jan 01 12:00:00`), you **must** include `rebase => true` to prevent parsing failures or out-of-bounds dates.  
> 2. **Strict Isolation Rule (Do Not Combine Formats):** Never combine patterns that *contain a year* and patterns that *lack a year* inside the same `match` array block.  
>    * **Why?** The `rebase => true` flag applies globally to the entire filter block. Mixing them will cause unpredictable timestamp math and structural ingestion errors for formats that already provide an explicit year.

##### **Correct Syntax Example (Isolated Missing Year Block)**

```
date {
  # ONLY matches formats that lack a year
  match  => ["when", "MMM dd HH:mm:ss"]
  rebase => true
}
```

#### **Drop**

The `drop` function completely discards an event, halting all further processing and preventing the message from being written to the output destination. It is typically wrapped inside conditional statements to filter out noise, health checks, or unparsable data.

##### 

##### **Drop Tag Metadata**

Before dropping a message, it is standard practice to flag the event with a specific tag to identify *why* it was discarded during pipeline execution or debugging. Common structural tags include:

* `TAG_MALFORMED_MESSAGE`: The log format does not match the expected structural layout.  
* `TAG_UNSUPPORTED`: The application or log source type is deliberately not supported by this parser configuration.  
* `TAG_MALFORMED_ENCODING`: The log payload contains bad character sets, corrupted bytes, or broken encoding strings.  
* `TAG_NO_SECURITY_VALUE`: The log event represents normal background chatter that holds no analytical or security intelligence value.

##### **Syntax & Example**

The `drop {}` block takes no internal parameters. 

**Implementation Example (Conditional Drop with Tagging)**

```
if [domain] == "-" {
  drop {
    tag => "TAG_NO_SECURITY_VALUE" 
  }
}
```

#### **Conditional Logics**

Conditional statements control the flow of execution within the parser configuration. In this parsing environment, conditionals are strictly limited to the **filter logic block** for event transformation.

##### **Supported Conditional Structures**

The parsing engine supports three primary conditional routing pathways:

* `if`  
* `if / else`  
* `if / else if / else`

#####  **Comparison & Regex Operators**

When evaluating conditional expressions, use the standard operators detailed in the table below:

| Operator | Description | Syntax Example |
| ----- | ----- | ----- |
| `==` | Equality / Exact match | `if [proto] == "tcp"` |
| `!=` | Inequality / Not equal | `if [status] != "200"` |
| `<` | Less than | `if [bytes] < 512` |
| `>` | Greater than | `if [bytes] > 1024` |
| `<=` | Less than or equal to | `if [severity] <= 3` |
| `>=` | Greater than or equal to | `if [severity] >= 4` |
| `=~` | Regular expression match | `if [action] =~ /deny|block/` |
| `!~` | Regular expression does not match | `if [url] !~ /abc\.com/` |

💡 **Boolean Operators:** Combine expressions using the **`and`** and **`or`** logical operators.

##### **Configuration Syntax & Examples**

##### **Basic `if` Statement**

Executes a code block only if the defined condition evaluates to true.

```
if [token] == "value" {
  # <code block>
}
```

**Example**

```
if [protocol] == "tcp" or [protocol] == "udp" or [protocol] == "icmp" {
  mutate {
    uppercase => [ "protocol" ]
  }
}
```

##### 

##### **`if / else` Block**

Evaluates multiple expressions using boolean operators, routing to a fallback block if the condition fails.

```
if [token1] == "value1" and [token2] == "value2" {
  # <code block 1>
} else {
  # <code block 2>
}
```

##### 

##### **`if / else if / else` Chain**

Evaluates sequential, mutually exclusive conditions to categorize data paths.

```
if [token] == "value1" {
  # <code block 1>
} else if [token] == "value2" {
  # <code block 2>
} else {
  # <code block 3>
}
```

**Example**

```
if [action] == "drop" or [action] == "deny" or [action] == "drop ICMP" {
  mutate {
    replace => { "event.webproxy.action" => "BLOCKED" }
  }
} else if [action] == "allow" {
  mutate {
    replace => { "event.webproxy.action" => "ALLOWED" }
  }
} else {
  mutate {
    replace => { "event.webproxy.action" => "OTHER" }
  }
}
```

#### **for loop**

Use the `for in` syntax when you need to loop through an iterable array or list of fields. The loop processes each item sequentially, allowing you to execute common logic on multiple tokens without duplicating code blocks.  
Index starts from “0”.

```
# Input Array Example:
# ports_list = ["srcport", "dstport"]

for port in ports_list {
  mutate {
    convert => { port => "integer" }
  }
}
```

##### 

##### **Map in for loop**

**Dictionary / Object Loops (`for key, value in ... map {}`):** Use the `map {}` extension when looping through an object containing explicit key-value pairs . The syntax automatically unrolls each dictionary entry, assigning the left side to your key variable and the right side to your value variable.

```
# Input Dictionary Map Example:
# priority_map = { "high" => "1", "medium" => "2", "low" => "3" }

for severity, udmseverity in priority_map map {
  if [severity_text] == severity {
    mutate {
      replace => { "event.webproxy.severity" => udmseverity }
    }
  }
}
```

### **4.Handling UDM enum values**

**Predefined UDM Enum Mapping:** 

UDM fields that use enumerated lists will **only** accept the specific predefined values defined by that enum. If you attempt to map any other arbitrary string or unsupported value, the platform will drop the value or fail validation.

If the incoming value does not match a known enum value, you must handle it explicitly (such as using an allowed fallback like `UNKNOWN_ACTION`) instead of passing the raw string.

**No `on_error` Required for Enums:** You do not need to write `on_error` flags for enum mappings since you are using static value replacements.

**Example:**  
UDM fields like “security\_result.action”, “security\_result.severity”, “network.ip\_protocol”

```
# ✅ GOOD PRACTICE: Mapping fixed Enums safely without requiring on_error
if [raw_action] =~ /^(block|blocked|deny|dropped)$/ {
  mutate {
    replace => { "security_result.action" => "BLOCK" }
  }
} else if [raw_action] =~ /^(allow|allowed|permit|pass)$/ {
  mutate {
    replace => { "security_result.action" => "ALLOW" }
  }
} else {
  mutate {
    replace => { "security_result.action" => "UNKNOWN_ACTION" }
  }
}
```

### **5\. Deprecated UDM Fields**

**🚫 Deprecated UDM Fields**

* **Avoid Deprecated Fields:** Do not map raw log data to  fields that are marked as deprecated in the Unified Data Model (UDM) schema. The platform will not support these attributes, and using them can cause schema validation failures, broken detection rules, or lost data.  
* **Map Only to Active Schema Attributes:** Always use the current, supported fields from the latest UDM schema documentation. 

```
# ❌ BAD PRACTICE: Mapping data to a deprecated UDM field
if [resource_id] != "" {
   mutate {
     replace => { 
        "target.resource.id" => "%{resource_id}" 
}
on_error => "invalid_resource_id"

    }
 }

# ✅ GOOD PRACTICE: Mapping data to the current, active UDM field
if [resource_id] != "" {
   mutate {
     replace => { 
        "target.resource.product_object_id" => "%{resource_id}" 
}
on_error => "invalid_resource_id"

    }
 }
```

### **6\. Error Handling**

**on\_error :**

The `on_error` property is a built-in safety mechanism that can be applied to filters to intercept and catch execution failures. Rather than allowing an exceptional condition (like a failed data type conversion) to crash the processing pipeline or disrupt log flow, `on_error` flags the event so you can handle it gracefully via conditional logic.

##### **Operational Mechanics**

* **Boolean Flagging:** The `on_error` configuration accepts a string value, which names a temporary boolean token.  
* **State Behavior:** If the filter executes successfully, the named token evaluates to `false`. If an exception or processing error occurs during that specific filter operation, the token is automatically set to `true`.

##### **On\_Error Syntax**

```
on_error => “<value>”
```

##### **On\_Error Function Example**

For example, you can use the on\_error function to check if a value is an IP address without causing a failure. A use case for this function is to determine if the field value is an IP address or hostname, and then handle the field value appropriately.

```
mutate {
  convert => {
    "host" => "ipaddress"
  }
 on_error => "is_not_ip"
}

if [is_not_ip] {
  # This means it's not an IP
}
```

### **7\. Statedump Validating Value Extraction and Assignment** 

The `statedump` filter is an inspection tool used to validate token extraction, field assignments, and pipeline variables during the development phase. It generates a structural, JSON-formatted snapshot of the parser's entire internal state at the exact moment the event hits the filter block.

🛑 **Production Restriction:** The `statedump` filter is strictly an offline debugging utility. It **cannot** be included in configurations submitted to production environments.

##### **Operational Capabilities**

* **State Visibility:** The output includes every token, variable value, metadata field, and internal flag currently set and visible within the processing pipeline.  
* **Flow Tracking:** By placing multiple dump points across your logic, you can trace exactly how your data transforms step by step.

##### **Configuration Syntax**

The filter block can be initialized completely empty, or with an optional `label` parameter. Using labels is highly recommended when embedding multiple dumps so you can easily distinguish which parts of your configuration logic generated each state block.

##### **Basic Syntax**

```
statedump {}
```

##### **Syntax with Label**

```
statedump {
  label => "your_custom_label"
}
```

##### 

##### **Implementation Example**

This snippet demonstrates how to leverage tagged states to isolate an issue right before a dangerous or complex operation:

```
# Capture the pipeline state before attempting a mutation
statedump {
  label => "pre_transformation"
}

mutate {
  gsub => [ "raw_payload", "cat", "dog" ]
}

# Capture the pipeline state immediately after to verify the result
statedump {
  label => "post_transformation"
}
```

### **8\. Data Output**

Use the merge function to generate output. It is possible to generate more than one event message based on a single log line. For example, you might want to create the web proxy event message, but also generate an alert message.

##### **Generating Output \- Single Event**

```
mutate {
  merge => {
    "@output" => "event"
  }
}
```

##### **Generating Output \- Multiple Events**

```
mutate {
  merge => {
    "@output" => "event1"
  }
}

mutate {
  merge => {
    "@output" => "event2"
  }
}
```

## 

## **Best Practices** 

**The Value of Parsing Everything:**   
Extract all available fields and parameters from the raw log at the time of parsing a new log to maximize parsing efficiency and reduce downstream computation. By structuring the complete log upfront, customers can immediately write detection rules against any field in the dataset without needing to update the parser, rewrite code, or replay historical logs when new threats emerge.

**Accurate Filter Matching:**  
 Use the most accurate filter specifically designed for your log format. For example, use a `kv` filter for KV logs , rather than writing heavy or inefficient `grok` expressions to parse them.

**Strict Schema Mapping Hierarchy:**   
Organize your code sequentially and map fields to the UDM structure using this exact priority order: 

* `Metadata`  
  * `Principal`  
  * `Target`  
  * `Intermediary`  
  * `Observer`  
  * `About`  
  * `Network`  
  * `Security_result`  
  * `additional`  
  * `metadata.event_type`  
  * `Metadata.product_name and metadata.vendor_name`

**Validation Checks for event\_type assignment:**  
Always verify specific UDM validation rules before setting `metadata.event_type`. Certain event types strictly require specific fields to be populated; for example, setting `STATUS_UPDATE` requires that `principal` data is present. Use conditional blocks to check for these mandatory fields before applying the event type.

```
if [has_principal] == "true" {
  mutate {
    replace => { "metadata.event_type" => "STATUS_UPDATE" }
  }
}
```

**Dynamic Mapping for Polymorphic Variables:**   
When a single log field can contain different types of data depending on the event (such as a `host` field arriving as a raw IP address in one log, but a hostname string in another), do not map it blindly. You must write conditional logic to validate the content type and route it to the correct target UDM attribute (e.g., `principal.ip` vs. `principal.hostname`).  
Same goes for email address / userid.

```
if [remote_request_ip] != "" {
    grok {
      match => {
        "remote_request_ip" => "%{IP:remote_request_ip}"
      }
      overwrite => ["remote_request_ip"]
      on_error => "remote_request_ip_grok_failure"
    }
    if ![remote_request_ip_grok_failure] {
      mutate {
        merge => {
          "principal.ip" => "remote_request_ip"
        }
        on_error => "remote_request_ip_empty"
      }
    }
    else {
      mutate {
        replace => {
          "principal.hostname" => "%{remote_request_ip}"
        }
        on_error => "remote_request_ip_hostname_empty"
      }
    }
  }
```

**Exhaustive Enum Mapping:**   
Ensure you account for all possible variations when mapping enum UDM fields based on raw log field. For example, if you have a log with field “action” as “allow” and you are mapping `security_result.action` to `ALLOW` , additionally map `security_result.action` to `BLOCK` considering the raw log value contains terms like `block`, `blocked`, or `deny`.

**Field Validation:** Always implement structural checks for fields that must conform to a specific format—such as email addresses, IP addresses, MAC addresses, or cryptographic hashes—before processing them or mapping them to the schema. This ensures malformed data is caught early and does not cause pipeline or index errors.

Example :

```
if [email_field] =~ "^.+@.+$"{
  mutate {
    merge => { "principal.user.email_address" => "email_field" 
}
on_error => "invalid_email"
  }
} 
```

**Unified Mapping Consolidation:**   
Group all the mappings in the same place in the configuration file if a single UDM field relies on mapping inputs from multiple source fields. Do not scatter mappings for a single destination field across different code blocks.

```
# ❌ BAD PRACTICE: Mappings scattered across separate blocks with generic errors
if [src_ip] != "" {
  mutate { 
    merge => { "principal.ip" => "src_ip" } 
    on_error => "src_ip_merge_failed"
  }
}
# ... hundreds of lines of code in between ...
if [client_ip] != "" {
  mutate { 
    merge => { "principal.ip" => "client_ip" } 
    on_error => "client_ip_merge_failed"
  }
}

# ✅ GOOD PRACTICE: Consolidated mapping logic with unique on_error tracking
if [src_ip] != "" {
  mutate { 
    merge => { "principal.ip" => "src_ip" } 
    on_error => "err_principal_ip_src"
  }
} 
if [client_ip] != "" {
  mutate { 
    merge => { "principal.ip" => "client_ip" } 
    on_error => "err_principal_ip_client"
  }
}
```

**Upfront Initialization & Null Safety:**  
 Declare and initialize all required fields at the very beginning of the filter configuration. Always implement explicit null or presence checks before attempting to map these values to the final schema.

**Grok Variables Management:**   
When using `grok` to extract  variables, ensure they are initialized before. Follow up by systematically overwriting these variables as your logic progresses, ensuring that the final mapped state is accurate and free of stale extraction data.

**Memory Efficiency via Variable Reuse:**   
Favor tokens and variables that are already instantiated in memory instead of continuously creating redundant, temporary custom fields.

**Single Responsibility Principle:**   
Keep different operations separated into individual mutate blocks to enforce the Single Responsibility Principle. Never mix different actions like `rename` and `replace` inside a single `mutate` block.

**Strict Adherence to DRY Principles:**   
Eliminate structural redundancies and duplicate extraction patterns to keep the configuration clean and maintainable.Strictly follow DRY principles.

**No Loop Iteration Underscores:**   
Avoid using a standalone underscore (`_`) as a loop or iterator variable name under any circumstances.

**Unified Lowercase Naming Conventions:**  
 Eliminate `camelCase` identifiers entirely. All user-defined tokens must use lowercase alphanumeric characters with `snake_case` if separators are required.

**Self-Explanatory unique `on_error` Flags:** Declare a unique, highly descriptive token name for every individual `on_error` tag. Never reuse the same error flag token across multiple filter actions.

### 
