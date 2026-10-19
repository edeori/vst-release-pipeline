"""Resolve release destinations from the existing Moth Production shop registry."""
import json
import os
import re
import urllib.request


def validate(config, product_id, repository):
    if config.get("repository", "").lower() != repository.lower():
        raise ValueError("Shop repository does not match the workflow repository")
    if config.get("bucket") != "downloads":
        raise ValueError("Only the downloads bucket is supported")
    result = {"bucket": "downloads"}
    for platform, directory, extension in (("mac", "mac", "pkg"), ("windows", "win", "exe")):
        key = config.get(platform + "_key", "")
        pattern = rf"(?:plugins|apps)/{re.escape(product_id)}/{directory}/[A-Za-z0-9_-]+\.{extension}"
        if not re.fullmatch(pattern, key):
            raise ValueError(f"Invalid {platform} destination: use a stable, version-free filename")
        result[platform + "_key"] = key
    return result


# Never forward the registry credential to redirects.
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    product_id = os.environ["PRODUCT_ID"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", product_id):
        raise ValueError("Invalid product ID")
    request = urllib.request.Request(
        "https://mothproduction.hu/release-api/products/" + product_id,
        headers={"Authorization": "Bearer " + os.environ["REGISTRY_TOKEN"]},
    )

    with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
        config = json.load(response)
    values = validate(config, product_id, os.environ["SOURCE_REPOSITORY"])
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
