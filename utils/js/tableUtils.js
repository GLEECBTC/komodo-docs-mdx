/**
 * Utility functions for working with CompactTable component
 */

/**
 * Convert legacy table data with separate Required/Default columns to CompactTable format
 * @param {Array} rows - Array of objects with parameter, type, required, default, description
 * @returns {Array} Formatted data for CompactTable
 */
export const convertLegacyTableData = (rows) => {
  return rows.map(row => {
    const converted = {
      parameter: row.parameter || row.Parameter,
      type: row.type || row.Type,
      required: parseRequired(row.required || row.Required),
      description: row.description || row.Description
    };

    // Handle default values
    const defaultValue = row.default || row.Default;
    if (defaultValue && defaultValue !== '-' && defaultValue !== '`-`') {
      converted.default = defaultValue;
    }

    return converted;
  });
};

/**
 * Parse various required field formats into boolean
 * @param {*} required - The required field value
 * @returns {boolean} True if required, false otherwise
 */
const parseRequired = (required) => {
  if (typeof required === 'boolean') return required;
  if (typeof required === 'string') {
    const normalized = required.toLowerCase().trim();
    return normalized === '✓' || 
           normalized === 'true' || 
           normalized === 'yes' || 
           normalized === 'required' ||
           normalized === '1';
  }
  return false;
};

/**
 * Convert markdown table string to CompactTable data format
 * @param {string} markdownTable - Markdown table string
 * @returns {Array} Parsed data for CompactTable
 */
export const parseMarkdownTable = (markdownTable) => {
  const lines = markdownTable.trim().split('\n');
  
  // Remove header separator line (the one with dashes)
  const headerLine = lines[0];
  const dataLines = lines.slice(2); // Skip header and separator
  
  // Parse header to get column names
  const headers = headerLine.split('|').map(h => h.trim()).filter(h => h);
  
  // Parse data rows
  const data = dataLines.map(line => {
    const cells = line.split('|').map(c => c.trim()).filter(c => c);
    const row = {};
    
    headers.forEach((header, index) => {
      const normalizedHeader = header.toLowerCase();
      let value = cells[index] || '';
      
      // Clean up cell content
      value = value.replace(/`([^`]+)`/g, '$1'); // Remove backticks
      value = value.replace(/^\s*\*\*([^*]+)\*\*\s*$/, '$1'); // Remove bold markdown
      
      if (normalizedHeader.includes('parameter')) {
        row.parameter = value;
      } else if (normalizedHeader.includes('type')) {
        row.type = value;
      } else if (normalizedHeader.includes('required')) {
        row.required = parseRequired(value);
      } else if (normalizedHeader.includes('default')) {
        if (value && value !== '-') {
          row.default = value;
        }
      } else if (normalizedHeader.includes('description')) {
        row.description = value;
      }
    });
    
    return row;
  });
  
  return convertLegacyTableData(data);
};

/**
 * Generate CompactTable JSX from data array
 * @param {Array} data - Table data
 * @param {Object} options - Options for table generation
 * @returns {string} JSX string
 */
export const generateCompactTableJSX = (data, options = {}) => {
  const {
    variant = 'default',
    columns = ['Parameter', 'Type', 'Description'],
    className = ''
  } = options;
  
  const dataStr = JSON.stringify(data, null, 2);
  const columnsStr = JSON.stringify(columns);
  
  return `<CompactTable 
  ${variant !== 'default' ? `variant="${variant}"` : ''}
  ${className ? `className="${className}"` : ''}
  data={${dataStr}}
  columns={${columnsStr}}
/>`;
};

/**
 * Validate CompactTable data structure
 * @param {Array} data - Data to validate
 * @returns {Object} Validation result with errors array
 */
export const validateTableData = (data) => {
  const errors = [];
  
  if (!Array.isArray(data)) {
    errors.push('Data must be an array');
    return { valid: false, errors };
  }
  
  data.forEach((row, index) => {
    if (!row.parameter) {
      errors.push(`Row ${index + 1}: Missing parameter name`);
    }
    if (!row.type) {
      errors.push(`Row ${index + 1}: Missing type`);
    }
    if (!row.description) {
      errors.push(`Row ${index + 1}: Missing description`);
    }
    if (row.required !== true && row.required !== false && row.required !== undefined) {
      errors.push(`Row ${index + 1}: Required field must be boolean or undefined`);
    }
  });
  
  return {
    valid: errors.length === 0,
    errors
  };
};

/**
 * Example usage and test data
 */
export const exampleData = {
  // Legacy format with separate columns
  legacy: [
    {
      parameter: "coin",
      type: "string",
      required: "✓",
      default: "-",
      description: "The name of the coin the user desires to activate."
    },
    {
      parameter: "amount",
      type: "float",
      required: "✗",
      default: "false",
      description: "The amount of balance to send."
    }
  ],
  
  // CompactTable format
  compact: [
    {
      parameter: "coin",
      type: "string",
      required: true,
      description: "The name of the coin the user desires to activate."
    },
    {
      parameter: "amount",
      type: "float",
      required: false,
      default: "false",
      description: "The amount of balance to send."
    }
  ]
};

// Example markdown table
export const exampleMarkdownTable = `
| Parameter | Type   | Required | Default | Description |
| --------- | ------ | :------: | :-----: | ----------- |
| coin      | string |    ✓     |   \`-\`   | The name of the coin the user desires to activate. |
| amount    | float  |    ✗     | \`false\` | The amount of balance to send. |
`;

// Usage example:
// const converted = convertLegacyTableData(exampleData.legacy);
// const jsx = generateCompactTableJSX(converted, { variant: 'compact' }); 