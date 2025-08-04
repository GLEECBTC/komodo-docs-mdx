import React from 'react';
import './CompactTable.css';

const CompactTable = ({ 
  data, 
  columns = ['Parameter', 'Type', 'Description'],
  className = '',
  variant = 'default' // 'default', 'compact', 'minimal'
}) => {
  const renderCell = (item, column) => {
    if (column.toLowerCase() === 'parameter') {
      const isRequired = item.required === true || item.required === '✓' || item.required === 'true';
      
      return (
        <span className={`parameter-name ${isRequired ? 'required' : 'optional'}`}>
          {item.parameter}
          {isRequired && (
            <span className="required-indicator" aria-label="required" title="Required parameter">
              *
            </span>
          )}
        </span>
      );
    }
    
    if (column.toLowerCase() === 'type') {
      return <code className="type-indicator">{item.type}</code>;
    }
    
    if (column.toLowerCase() === 'description') {
      let description = item.description;
      
      // Handle legacy format where required/default info is in separate columns
      if (item.required === false || item.required === '✗' || item.required === 'false') {
        const defaultValue = item.default && item.default !== '-' ? item.default : null;
        const prefix = defaultValue ? `Optional, defaults to \`${defaultValue}\`. ` : 'Optional. ';
        description = description.startsWith('Optional') ? description : prefix + description;
      }
      
      return description;
    }
    
    return item[column.toLowerCase()];
  };

  return (
    <div className={`compact-table-wrapper ${variant} ${className}`}>
      <table className="compact-table" role="table">
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th key={index} scope="col">
                {column}
                {column.toLowerCase() === 'parameter' && (
                  <span className="required-legend" title="* indicates required parameter">
                    <span className="required-asterisk">*</span> = required
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item, index) => (
            <tr key={index}>
              {columns.map((column, colIndex) => (
                <td key={colIndex}>
                  {renderCell(item, column)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default CompactTable; 