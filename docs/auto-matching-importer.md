# AutoMatchingImporter

The `AutoMatchingImporter` class is a component of the Pos Exporter module that facilitates the automatic matching and synchronization of records between Odoo and the Point of Sale (Pos) system. It compares the values of specified fields between Odoo and Pos records and creates the mappings accordingly.

## Purpose

The `AutoMatchingImporter` class is designed to simplify the synchronization process by automatically matching records based on specified field values. It retrieves records from both Odoo and the Pos system, compares the values of designated fields, and creates the mappings between the corresponding records.

## Usage

To use the `AutoMatchingImporter` class, you need to inherit from it and implement the necessary methods and attributes:

- `_erp_field`: The field in the external system (Pos) that corresponds to the field in Odoo.
- `_pos_field`: The field in Odoo that corresponds to the field in the external system (Pos).
- `_copy_fields`: A list of tuples specifying the fields to copy from Pos to Odoo during the synchronization.
- `_filters`: Additional filters to be applied when querying records from the Pos system.
- `_compare_function`: A method that compares the values of the designated fields between Odoo and Pos records and determines if they match.

You also need to implement the `run()` method, which executes the synchronization process. Within this method, the `AutoMatchingImporter` retrieves the records from Odoo and Pos, compares their field values, and creates the mappings between them.

## Configuration

Before running the `AutoMatchingImporter`, you need to configure the necessary settings for establishing the connection between Odoo and the Pos system. This includes configuring the field mappings, defining the filters, and setting up the necessary connections to the external systems.

## Methods

The `AutoMatchingImporter` provides the following method:

- `run()`: Executes the synchronization process. It retrieves records from Odoo and Pos, compares the field values, and creates the mappings between the corresponding records.

## Logging and Reporting

During the synchronization process, the `AutoMatchingImporter` logs various information and generates reports regarding the number of records already mapped, the number of records successfully mapped, and the number of records that could not be mapped.

## Extensibility

The `AutoMatchingImporter` class can be extended to customize the synchronization process according to the specific requirements of the Pos system being integrated. You can override the `_compare_function` method to implement custom comparison logic or extend the `run()` method to include additional steps or validations.

## Error Handling

The `AutoMatchingImporter` class should handle potential errors and exceptions that may occur during the synchronization process. This includes handling errors related to data retrieval, comparison failures, mapping creation, and any other synchronization-related issues. Proper error handling ensures the reliability and consistency of the synchronization process.

## Contributing

Contributions to the Pos Exporter module, including the `AutoMatchingImporter` class, are welcome! If you encounter any issues or have suggestions for improvements, please open an issue or submit a pull request on the repository.

## License

The Pos Exporter module, including the `AutoMatchingImporter` class, is licensed under the MIT License. See the [LICENSE](../LICENSE) file for more details.

