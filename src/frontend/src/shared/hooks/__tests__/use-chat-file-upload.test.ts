import { isAllowedChatAttachmentFile } from "@/utils/fileUtils";

describe("isAllowedChatAttachmentFile", () => {
  it("allows png by extension and mime type", () => {
    const file = new File(["test"], "photo.png", { type: "image/png" });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("allows jpg with jpeg mime type", () => {
    const file = new File(["test"], "photo.jpg", { type: "image/jpeg" });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("allows pdf files", () => {
    const file = new File(["test"], "report.pdf", {
      type: "application/pdf",
    });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("allows csv files", () => {
    const file = new File(["name,age\nAda,32"], "data.csv", {
      type: "text/csv",
    });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("allows docx files", () => {
    const file = new File(["test"], "report.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("blocks extension spoofing when mime type is non-image", () => {
    const file = new File(["test"], "report.png", {
      type: "application/pdf",
    });

    expect(isAllowedChatAttachmentFile(file)).toBe(false);
  });

  it("allows files without extension when mime type is allowed image", () => {
    const file = new File(["test"], "clipboard", {
      type: "image/png",
    });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("allows extension-based image files when mime type is unavailable", () => {
    const file = new File(["test"], "pasted.jpeg", { type: "" });

    expect(isAllowedChatAttachmentFile(file)).toBe(true);
  });

  it("blocks unsupported extension when mime type is unavailable", () => {
    const file = new File(["test"], "data.exe", { type: "" });

    expect(isAllowedChatAttachmentFile(file)).toBe(false);
  });
});
