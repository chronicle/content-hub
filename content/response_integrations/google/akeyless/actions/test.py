import akeyless

def test_access_secret():
    # --- ENTER YOUR AKEYLESS CREDENTIALS HERE ---
    access_id = "p-h2hr9q4ew015am"
    access_key = "yLWsJTAIBqV4jyIECfrP5iZ2mRwzGmrkgW2q2K+bLlc="
    secret_name = "/db-password"      # Ensure this matches your secret path exactly (e.g., /db-password or /my-secrets/db-password)
    gateway_url = "https://api.akeyless.io"
    access_type = "access_key"         # Default is access_key
    # ---------------------------------------------

    print("==================================================")
    print("Akeyless Local Connectivity and Access Test")
    print("==================================================")
    print(f"Access ID   : {access_id}")
    print(f"Gateway URL : {gateway_url}")
    print(f"Secret Name : {secret_name}")
    print("--------------------------------------------------")

    # 1. Configure the API client
    print("1. Initializing Akeyless API Client...")
    configuration = akeyless.Configuration()
    configuration.host = gateway_url
    api_client = akeyless.ApiClient(configuration)
    api = akeyless.V2Api(api_client)

    try:
        # 2. Authenticate and fetch session token
        print("2. Authenticating with Akeyless...")
        auth_body = akeyless.Auth(
            access_id=access_id,
            access_key=access_key,
            access_type=access_type
        )
        auth_response = api.auth(auth_body)
        token = auth_response.token
        print("   -> Authentication Successful!")
        print(f"   -> Session Token Retrieved: {token[:12]}... (len: {len(token)})")

        # 3. Access the static secret value
        print(f"3. Retrieving Secret Value for '{secret_name}'...")
        secret_body = akeyless.GetSecretValue(
            names=[secret_name],
            token=token
        )
        response = api.get_secret_value(secret_body)

        # 4. Parse the response
        if isinstance(response, dict):
            secret_val = response.get(secret_name)
        elif hasattr(response, "get"):
            secret_val = response.get(secret_name)
        else:
            secret_val = getattr(response, secret_name, None)

        if secret_val is not None:
            print("   -> Secret Value Accessed Successfully!")
            print("--------------------------------------------------")
            print(f"SECRET PAYLOAD VALUE: {secret_val}")
            print("--------------------------------------------------")
            print("SUCCESS: The setup, role permissions, and secret retrieval are working perfectly!")
        else:
            print("   -> ERROR: Secret name resolved, but the response value was empty/None.")
            print(f"   -> Full response object was: {response}")

    except akeyless.exceptions.ApiException as api_err:
        print("\n[API ERROR ENCOUNTERED]")
        print(f"Status Code: {api_err.status}")
        print(f"Reason: {api_err.reason}")
        print(f"Message: {api_err.body}")
        print("\nTroubleshooting Tips:")
        print("- Verify your Access ID and Access Key match exactly.")
        print("- Check if the Auth Method (Access ID) is correctly associated with the Role in Step 3.")
        print("- Ensure the Role has 'Read' capabilities for the path you specified.")
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR]: {e}")

if __name__ == "__main__":
    test_access_secret()

