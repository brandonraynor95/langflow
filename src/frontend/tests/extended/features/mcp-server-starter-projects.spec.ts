import { expect, test } from "@playwright/test";
import { awaitBootstrapTest } from "../../utils/await-bootstrap-test";
import { cleanOldFolders } from "../../utils/clean-old-folders";
import { convertTestName } from "../../utils/convert-test-name";
import { navigateSettingsPages } from "../../utils/go-to-settings";

test(
  "user must be able to see starter projects for mcp servers",
  { tag: ["@release", "@workspace", "@components"] },
  async ({ page }) => {
    //starter mcp project

    await awaitBootstrapTest(page, {
      skipModal: true,
    });

    await cleanOldFolders(page);

    await navigateSettingsPages(page, "Settings", "MCP Servers");

    expect(await page.getByTestId("mcp_server_name_0").textContent()).toContain(
      "lf-starter_project",
    );

    await page.getByTestId("icon-ChevronLeft").first().click();

    //add new folders

    await page.getByTestId("add-project-button").click();
    await page.getByTestId("add-project-button").click();

    await navigateSettingsPages(page, "Settings", "MCP Servers");

    expect(await page.getByTestId("mcp_server_name_0").textContent()).toContain(
      "lf-starter_project",
    );

    expect(
      await page.getByText("lf-new_project", { exact: true }).count(),
    ).toBe(1);
    expect(
      await page.getByText("lf-new_project_1", { exact: true }).count(),
    ).toBe(1);

    await page.getByTestId("icon-ChevronLeft").first().click();

    //rename a folder

    const getFirstFolderName = convertTestName(
      (await page.getByText("New Project").first().textContent()) as string,
    );

    await page
      .getByText("New Project")
      .first()
      .hover()
      .then(async () => {
        await page
          .getByTestId(`more-options-button_${getFirstFolderName}`)
          .last()
          .click();
        await page.getByText("Rename", { exact: true }).last().click();
        await page.getByTestId("input-project").last().fill("renamed_project");
        await page.keyboard.press("Enter");
        await page.waitForTimeout(1000);
      });

    await navigateSettingsPages(page, "Settings", "MCP Servers");

    expect(await page.getByTestId("mcp_server_name_0").textContent()).toContain(
      "lf-starter_project",
    );

    expect(
      await page.getByText("lf-renamed_project", { exact: true }).count(),
    ).toBe(1);

    //delete a folder

    await page.getByTestId("icon-ChevronLeft").first().click();
    await page
      .getByTestId("sidebar-nav-renamed_project")
      .hover()
      .then(async () => {
        await page
          .getByTestId("more-options-button_renamed_project")
          .last()
          .click();
        await page.getByText("Delete", { exact: true }).last().click();
        await page.getByText("Delete", { exact: true }).last().click();
        await page.waitForTimeout(1000);
      });

    await navigateSettingsPages(page, "Settings", "MCP Servers");

    expect(await page.getByTestId("mcp_server_name_0").textContent()).toContain(
      "lf-starter_project",
    );
    expect(
      await page.getByText("lf-renamed_project", { exact: true }).count(),
    ).toBe(0);
  },
);

test(
  "user must not be able to add duplicate mcp servers from starter projects",
  { tag: ["@release", "@workspace", "@components"] },
  async ({ page }) => {
    await awaitBootstrapTest(page);

    await page.getByTestId("side_nav_options_all-templates").click();
    await page.getByRole("heading", { name: "Basic Prompting" }).click();

    await page.waitForSelector('[data-testid="sidebar-search-input"]', {
      timeout: 100000,
    });

    await page.getByTestId("icon-ChevronLeft").first().click();

    await page.getByTestId("mcp-btn").click();
    await page.getByText("JSON").last().click();
    
    // Get the clipboard content to log what we're trying to add
    const clipboardHandle = await page.evaluateHandle(() => navigator.clipboard.readText());
    const clipboardContent = await clipboardHandle.jsonValue();
    console.log("=== CLIPBOARD CONTENT ===");
    console.log(clipboardContent);
    console.log("=== END CLIPBOARD ===");
    
    await page.getByTestId("icon-copy").click();

    await navigateSettingsPages(page, "Settings", "MCP Servers");

    await page.getByTestId("add-mcp-server-button-page").click();
    await page.getByTestId("json-input").click();
    await page.keyboard.press(`ControlOrMeta+V`);
    
    // Log the JSON input value
    const jsonInput = await page.getByTestId("json-input").inputValue();
    console.log("=== JSON INPUT VALUE ===");
    console.log(jsonInput);
    console.log("=== END JSON INPUT ===");
    
    // Set up console message listener to catch any errors
    page.on('console', msg => {
      console.log(`BROWSER CONSOLE [${msg.type()}]:`, msg.text());
    });
    
    // Set up response listener to catch API errors
    page.on('response', async response => {
      if (response.url().includes('/api/v1/mcp/')) {
        console.log(`=== API RESPONSE ===`);
        console.log(`URL: ${response.url()}`);
        console.log(`Status: ${response.status()}`);
        try {
          const body = await response.json();
          console.log(`Body:`, JSON.stringify(body, null, 2));
        } catch (e) {
          console.log(`Could not parse response body`);
        }
        console.log(`=== END API RESPONSE ===`);
      }
    });
    
    await page.getByTestId("add-mcp-server-button").click();

    // Wait a bit to see what happens
    await page.waitForTimeout(2000);
    
    // Check for any error messages on the page
    const pageContent = await page.content();
    console.log("=== CHECKING FOR ERROR MESSAGES ===");
    const hasServerExists = pageContent.includes("Server already exists");
    const hasValidationError = pageContent.includes("not allowed") || pageContent.includes("security");
    console.log(`Has "Server already exists": ${hasServerExists}`);
    console.log(`Has validation error: ${hasValidationError}`);
    console.log("=== END ERROR CHECK ===");

    // Wait for error message to appear
    await expect(page.getByText("Server already exists.")).toBeVisible({
      timeout: 10000,
    });

    const numberOfErrors = await page
      .getByText("Server already exists.")
      .count();
    expect(numberOfErrors).toBe(1);
  },
);
