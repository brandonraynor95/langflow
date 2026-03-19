const url = `${process.env.LANGFLOW_URL ?? ""}/api/v1/flows/upload/?folder_id=${process.env.FOLDER_ID ?? ""}`;

const formData = new FormData();
// Replace with a File/Blob for "agent-with-astra-db-tool.json" in your environment.
formData.append("file", new Blob(["<file contents>"]), "agent-with-astra-db-tool.json");

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
