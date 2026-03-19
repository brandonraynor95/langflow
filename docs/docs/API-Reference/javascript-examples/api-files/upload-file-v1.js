const url = `${process.env.LANGFLOW_URL ?? ""}/api/v1/files/upload/${process.env.FLOW_ID ?? ""}`;

const formData = new FormData();
// Replace with a File/Blob for "FILE_NAME.txt" in your environment.
formData.append("file", new Blob(["<file contents>"]), "FILE_NAME.txt");

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
