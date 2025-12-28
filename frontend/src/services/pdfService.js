import jsPDF from "jspdf";
import html2canvas from "html2canvas";

export const generatePDF = async (
  chatElementId,
  sessionTitle = "Prysm Analysis"
) => {
  const container = document.getElementById(chatElementId);
  if (!container) return;

  try {
    const pdf = new jsPDF({
      orientation: "p",
      unit: "mm",
      format: "a4",
    });

    // A4 Dimensions
    const pageWidth = 210;
    const pageHeight = 297;
    const margin = 10;
    const contentWidth = pageWidth - 2 * margin;
    const themeColor = "#0f172a"; // Match app background

    // Initial Cursor Position
    let yPos = margin;

    // Helper to add background to current page
    const fillPageBackground = () => {
      pdf.setFillColor(themeColor);
      pdf.rect(0, 0, pageWidth, pageHeight, "F");
    };

    // 1. Setup First Page
    fillPageBackground();

    // Add Header
    pdf.setTextColor(255, 255, 255);
    pdf.setFontSize(18);
    pdf.setFont("helvetica", "bold");
    pdf.text("Prysm Investment Report", margin, yPos + 6);

    pdf.setFontSize(10);
    pdf.setFont("helvetica", "normal");
    pdf.setTextColor(148, 163, 184); // slate-400
    pdf.text(
      `Generated on ${new Date().toLocaleDateString()}`,
      margin,
      yPos + 12
    );

    yPos += 20; // Move cursor down after header

    // 2. Iterate through children (messages)
    const messages = Array.from(container.children); // Get all message divs

    for (const message of messages) {
      // Skip empty or tiny elements
      if (message.offsetHeight < 5) continue;

      // Capture element
      const canvas = await html2canvas(message, {
        scale: 2,
        useCORS: true,
        backgroundColor: themeColor, // Ensure seamless bg
        logging: false,
      });

      const imgData = canvas.toDataURL("image/png");
      const imgProps = pdf.getImageProperties(imgData);

      // Calculate dimensions in PDF units (mm)
      const pdfImgHeight = (imgProps.height * contentWidth) / imgProps.width;

      // Check if element fits on current page
      if (yPos + pdfImgHeight > pageHeight - margin) {
        pdf.addPage();
        fillPageBackground(); // Background for new page
        yPos = margin; // Reset to top
      }

      // Add image
      pdf.addImage(imgData, "PNG", margin, yPos, contentWidth, pdfImgHeight);
      yPos += pdfImgHeight + 5; // Add gap between messages
    }

    // 3. Save
    const filename = `${sessionTitle.replace(/\s+/g, "_")}_${new Date()
      .toISOString()
      .slice(0, 10)}.pdf`;
    pdf.save(filename);
    return true;
  } catch (error) {
    console.error("PDF Generation failed:", error);
    return false;
  }
};
