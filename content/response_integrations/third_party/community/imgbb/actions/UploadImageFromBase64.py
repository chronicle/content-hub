from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "Imgbb"


@output_handler
def main():
    siemplify = SiemplifyAction()

    # Extracting the integration params
    conf = siemplify.get_configuration(INTEGRATION_NAME)
    api_key = conf.get("API Key")
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"

    url = f"https://api.imgbb.com/1/upload?expiration=600&key={api_key}"

    # Initializing the json_result
    json_result = {}

    # Extracting the action params- base64 image string
    image_in_base64 = siemplify.extract_action_param("Image in base64")

    # Determing the body params-for the request
    data = {"image": image_in_base64}

    response = requests.post(url, data=data, verify=verify_ssl)

    # Place the image details in image_details variable
    image_details = response.json()

    # Checking if the response content is in json format, otherwise it will raise an Exception
    try:
        response.json()
    except:
        raise Exception(response.content)

    response.raise_for_status()

    # Getting the value of the image url
    image_url_link = image_details["data"]["url"]

    # Checking the if image_url_link is None
    if image_url_link:
        json_result["url"] = image_url_link
        output_message = "The image was uploaded successfully. Image URL is available in the action result"
        result_value = True

    else:
        json_result["error_message"] = image_details["error"]["message"]
        output_message = "The image URL wasnt created"
        result_value = False

    # Adding the image URL link
    title = "Image URL link"
    link = image_url_link
    siemplify.result.add_link(title, link)

    # Adding json result to the action
    siemplify.result.add_result_json(json_result)

    siemplify.end(output_message, result_value)


3
if __name__ == "__main__":
    main()
