const url = `${process.env.LANGFLOW_URL ?? ""}/api/v1/projects/upload/`;

const formData = new FormData();
// Replace with a File/Blob for "20241230_135006_langflow_flows.zip" in your environment.
formData.append("file", new Blob(["<file contents>"]), "20241230_135006_langflow_flows.zip");

const options = {
  method: 'POST',
  headers: {
    "accept": `application/json`,
    "x-api-key": `${process.env.LANGFLOW_API_KEY ?? ""}`,
  },
  body: formData,
};

fetch(url, options)
  .then(async (response) => {
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const text = await response.text();
    console.log(text);
  })
  .catch((error) => console.error(error));
