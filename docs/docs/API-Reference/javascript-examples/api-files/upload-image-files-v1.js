const url = `${process.env.LANGFLOW_URL ?? ""}/api/v1/files/upload/${process.env.FLOW_ID ?? ""}`;

const formData = new FormData();
// Replace with a File/Blob for "PATH/TO/FILE.png" in your environment.
formData.append("file", new Blob(["<file contents>"]), "PATH/TO/FILE.png");

const options = {
  method: 'POST',
  headers: {
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
