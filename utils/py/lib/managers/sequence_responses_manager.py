#!/usr/bin/env python3
"""
Sequence-based Response Manager - Advanced KDF response collection with prerequisite handling.

This manager processes KDF methods in sequence order, handling prerequisites automatically
and providing a cleaner, more maintainable approach to response harvesting.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

# Import existing components
try:
    from .kdf_responses_manager import KdfResponseManager, KDFInstance, KDF_INSTANCES, CollectionResult
    from ..models.kdf_method import KdfMethod, KdfExample, MethodRequestQueue, KdfMethodsLoader, MethodStatus
    from ..utils.json_utils import dump_sorted_json
except ImportError:
    # Fall back to absolute imports
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from managers.kdf_responses_manager import KdfResponseManager, KDFInstance, KDF_INSTANCES, CollectionResult
    from models.kdf_method import KdfMethod, KdfExample, MethodRequestQueue, KdfMethodsLoader, MethodStatus
    from utils.json_utils import dump_sorted_json


@dataclass
class ProcessingStats:
    """Statistics for method processing."""
    total_methods: int = 0
    completed_methods: int = 0
    failed_methods: int = 0
    skipped_methods: int = 0
    prerequisite_cycles: int = 0
    total_examples: int = 0
    successful_examples: int = 0
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion rate as a percentage."""
        if self.total_methods == 0:
            return 0.0
        return (self.completed_methods / self.total_methods) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate example success rate as a percentage."""
        if self.total_examples == 0:
            return 0.0
        return (self.successful_examples / self.total_examples) * 100


class SequenceResponseManager(KdfResponseManager):
    """Enhanced response manager with sequence-based processing and prerequisite handling."""
    
    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize the sequence-based response manager."""
        super().__init__(workspace_root)
        
        self.method_queue: Optional[MethodRequestQueue] = None
        self.processed_prerequisites: Set[str] = set()
        self.stats = ProcessingStats()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def load_methods(self) -> MethodRequestQueue:
        """Load all KDF methods and create the processing queue."""
        self.logger.info("🔄 Loading KDF methods and creating processing queue...")
        
        self.method_queue = KdfMethodsLoader.load_from_files(self.workspace_root)
        
        # Calculate statistics
        self.stats.total_methods = len(self.method_queue.methods)
        self.stats.total_examples = sum(len(method.examples) for method in self.method_queue.methods.values())
        
        self.logger.info(f"📊 Loaded {self.stats.total_methods} methods with {self.stats.total_examples} total examples")
        self.logger.info(f"🔍 Methods by sequence:")
        
        # Group methods by sequence for logging
        sequence_groups = {}
        for method in self.method_queue.methods.values():
            if method.sequence not in sequence_groups:
                sequence_groups[method.sequence] = []
            sequence_groups[method.sequence].append(method.name)
        
        for sequence in sorted(sequence_groups.keys()):
            methods_list = sorted(sequence_groups[sequence])
            self.logger.info(f"   Sequence {sequence}: {len(methods_list)} methods - {', '.join(methods_list[:3])}{'...' if len(methods_list) > 3 else ''}")
        
        return self.method_queue
    
    def process_method_with_prerequisites(self, method: KdfMethod) -> bool:
        """Process a method, handling prerequisites automatically."""
        self.logger.info(f"🎯 Processing method: {method.name} (sequence: {method.sequence})")
        
        # Check if prerequisites need to be processed
        unmet_prerequisites = [prereq for prereq in method.prerequisites 
                             if prereq not in self.method_queue.completed_methods]
        
        if unmet_prerequisites:
            self.logger.info(f"📋 Method {method.name} has unmet prerequisites: {unmet_prerequisites}")
            
            # Process each prerequisite
            for prereq_name in unmet_prerequisites:
                if prereq_name in self.processed_prerequisites:
                    self.logger.info(f"   Prerequisite {prereq_name} already processed this cycle")
                    continue
                    
                prereq_method = self.method_queue.methods.get(prereq_name)
                if prereq_method:
                    self.logger.info(f"🔄 Processing prerequisite: {prereq_name}")
                    self.processed_prerequisites.add(prereq_name)
                    
                    # Recursively process prerequisite
                    prereq_success = self.process_method_with_prerequisites(prereq_method)
                    if prereq_success:
                        self.method_queue.mark_method_completed(prereq_name)
                    else:
                        self.logger.warning(f"⚠️ Prerequisite {prereq_name} failed, but continuing...")
                else:
                    self.logger.warning(f"⚠️ Prerequisite method {prereq_name} not found in queue")
            
            # Update method's prerequisite status
            method.mark_prerequisite_completed(prereq_name)
        
        # Now process the actual method
        return self.process_single_method(method)
    
    def process_single_method(self, method: KdfMethod) -> bool:
        """Process a single method and all its examples."""
        if not method.has_examples:
            self.logger.info(f"⚪ Skipping {method.name} - no examples available")
            self.stats.skipped_methods += 1
            return True
        
        method.status = MethodStatus.IN_PROGRESS
        method_success = True
        examples_processed = 0
        examples_successful = 0
        
        self.logger.info(f"📤 Processing {len(method.examples)} examples for {method.name}")
        
        for example_name, example in method.examples.items():
            try:
                # Skip manual methods/examples
                if example.is_manual:
                    self.logger.info(f"⚪ Skipping manual method/example: {method.name} ({example_name})")
                    self.stats.skipped_methods += 1
                    continue
                # Skip deprecated methods unless explicitly enabled
                if method.deprecated:
                    self.logger.info(f"⚪ Skipping deprecated method example: {example_name}")
                    continue
                
                self.logger.info(f"   🔄 Processing example: {example_name}")
                
                # Use the existing collection logic from UnifiedResponseManager
                result = self.collect_regular_method(example_name, example.request_data, method.name)
                
                # Update example with results
                if result.all_successful:
                    example.response_data = result.instance_responses
                    example.collected = True
                    examples_successful += 1
                    self.logger.info(f"   ✅ Example {example_name} succeeded")
                else:
                    example.error_data = result.instance_responses
                    example.collected = True
                    method_success = False
                    self.logger.info(f"   ❌ Example {example_name} had errors")
                
                examples_processed += 1
                
                # Store the result in our results collection
                self.results.append(result)
                
                # Skip response file updates for now - will be handled at the end
                
                # Small delay between examples to avoid overwhelming the API
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"❌ Error processing example {example_name}: {str(e)}")
                example.error_data = {"error": str(e)}
                example.collected = True
                method_success = False
        
        # Update statistics
        self.stats.successful_examples += examples_successful
        
        if method_success:
            method.status = MethodStatus.COMPLETED
            self.stats.completed_methods += 1
            self.logger.info(f"✅ Method {method.name} completed successfully ({examples_successful}/{examples_processed} examples)")
        else:
            method.status = MethodStatus.FAILED
            self.stats.failed_methods += 1
            self.logger.warning(f"⚠️ Method {method.name} completed with errors ({examples_successful}/{examples_processed} examples)")
        
        return method_success
    
    def collect_all_responses_sequenced(self) -> Dict[str, CollectionResult]:
        """Main method to collect all responses using sequence-based processing."""
        self.logger.info("🚀 Starting sequence-based response collection")
        
        # Load methods
        if not self.method_queue:
            self.load_methods()
        
        # Ensure response files exist (this method exists in the parent class)
        self._ensure_response_files_exist()
        
        # Process methods in sequence order
        max_cycles = 10000  # Prevent infinite loops
        cycle = 0
        
        while cycle < max_cycles:
            cycle += 1
            self.stats.prerequisite_cycles = cycle
            
            # Clear processed prerequisites for this cycle
            self.processed_prerequisites.clear()
            
            # Get next processable method
            next_method = self.method_queue.get_next_processable_method()
            
            if not next_method:
                # Check if there are methods waiting for prerequisites
                methods_needing_prereqs = self.method_queue.get_methods_needing_prerequisites()
                if methods_needing_prereqs:
                    self.logger.warning(f"🔄 Cycle {cycle}: No processable methods, but {len(methods_needing_prereqs)} methods need prerequisites")
                    # Try to process them anyway (prerequisites might be external)
                    for method in methods_needing_prereqs[:3]:  # Process up to 3 per cycle
                        self.logger.info(f"🔄 Attempting method with unmet prerequisites: {method.name}")
                        success = self.process_single_method(method)
                        if success:
                            self.method_queue.mark_method_completed(method.name)
                        else:
                            self.method_queue.mark_method_failed(method.name)
                    continue
                else:
                    self.logger.info(f"✅ All processable methods completed after {cycle} cycles")
                    break
            
            # Process the method
            self.logger.info(f"🔄 Cycle {cycle}: Processing {next_method.name}")
            success = self.process_method_with_prerequisites(next_method)
            
            if success:
                self.method_queue.mark_method_completed(next_method.name)
            else:
                self.method_queue.mark_method_failed(next_method.name)
            
            # Log progress
            if cycle % 5 == 0 or self.method_queue.pending_count <= 5:
                pending = self.method_queue.pending_count
                completed = self.method_queue.completed_count
                failed = self.method_queue.failed_count
                self.logger.info(f"📊 Progress: {completed} completed, {failed} failed, {pending} pending")
        
        if cycle >= max_cycles:
            self.logger.warning(f"⚠️ Reached maximum cycles ({max_cycles}), stopping processing")
        
        # Final statistics
        self.log_final_statistics()
        
        # Save collected addresses using wallet manager
        wallet_output_file = self.workspace_root / "postman/generated/reports/test_addresses.json"
        self.wallet_manager.save_test_addresses_report(wallet_output_file)
        
        # Fetch and log KDF version (prefer report extraction, no extra RPC)
        kdf_version = self.get_kdf_version_from_report() or self.get_kdf_version()
        if kdf_version:
            self.logger.info(f"Completed collecting responses from KDF version {kdf_version}")
        else:
            self.logger.info("Completed collecting responses (KDF version unknown)")

        return self.results
    
    def log_final_statistics(self):
        """Log comprehensive final statistics."""
        self.logger.info("📊 Final Processing Statistics:")
        self.logger.info(f"   Total Methods: {self.stats.total_methods}")
        self.logger.info(f"   ✅ Completed: {self.stats.completed_methods} ({self.stats.completion_rate:.1f}%)")
        self.logger.info(f"   ❌ Failed: {self.stats.failed_methods}")
        self.logger.info(f"   ⚪ Skipped: {self.stats.skipped_methods}")
        self.logger.info(f"   🔄 Prerequisite Cycles: {self.stats.prerequisite_cycles}")
        self.logger.info(f"   📤 Total Examples: {self.stats.total_examples}")
        self.logger.info(f"   ✅ Successful Examples: {self.stats.successful_examples} ({self.stats.success_rate:.1f}%)")
        
        # Address collection summary
        wallet_summary = self.wallet_manager.get_summary()
        self.logger.info(f"   🏦 Addresses Collected: {wallet_summary['total_addresses']} across {wallet_summary['total_instances']} environments")
        
        # Save processing statistics
        stats_file = self.workspace_root / "postman/generated/reports/processing_stats.json"
        stats_data = {
            "total_methods": self.stats.total_methods,
            "completed_methods": self.stats.completed_methods,
            "failed_methods": self.stats.failed_methods,
            "skipped_methods": self.stats.skipped_methods,
            "prerequisite_cycles": self.stats.prerequisite_cycles,
            "total_examples": self.stats.total_examples,
            "successful_examples": self.stats.successful_examples,
            "completion_rate": self.stats.completion_rate,
            "success_rate": self.stats.success_rate,
            "kdf_version": getattr(self, 'last_kdf_version', None),
            "addresses_collected": wallet_summary['total_addresses'],
            "environments": wallet_summary['total_instances']
        }
        
        dump_sorted_json(stats_data, stats_file)
        self.logger.info(f"📈 Processing statistics saved to {stats_file}")


def main():
    """Main function for running the sequence-based response manager."""
    import argparse
    import logging
    
    parser = argparse.ArgumentParser(description="KDF Sequence-based Response Manager")
    parser.add_argument(
        "--update-files", 
        action="store_true",
        help="Automatically update response files with successful responses"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Find workspace root
    current_dir = Path(__file__).parent
    workspace_root = current_dir
    while workspace_root.name != "komodo-docs-mdx" and workspace_root.parent != workspace_root:
        workspace_root = workspace_root.parent
    
    if workspace_root.name != "komodo-docs-mdx":
        raise RuntimeError("Could not find workspace root (komodo-docs-mdx)")
    
    # Create and run the manager
    manager = SequenceResponseManager(workspace_root)
    
    try:
        results = manager.collect_all_responses_sequenced()
        logging.info(f"🎉 Collection completed successfully! Processed {len(results)} method examples")
        
        # Compile results into the unified format
        unified_results = manager.compile_results()
        
        # Always validate both existing and collected responses
        validation_results = manager.validate_responses(validate_collected_responses=True)
        unified_results["validation"] = validation_results
        
        # Save results
        output_file = manager.workspace_root / "postman/generated/reports/kdf_postman_responses.json"
        manager.save_results(unified_results, output_file)
        
        # Save delay report
        reports_dir = manager.workspace_root / "postman/generated/reports"
        manager.save_delay_report(reports_dir)
        
        # Save inconsistent responses report
        manager.save_inconsistent_responses_report(reports_dir)
        
        # Regenerate missing responses report after response collection
        manager.regenerate_missing_responses_report(reports_dir)
        
        # Print collection summary
        metadata = unified_results.get("metadata", {})
        logging.info(f"📊 Total responses collected: {metadata.get('total_responses_collected', 0)}")
        logging.info(f"📊 Auto-updatable responses: {metadata.get('auto_updatable_count', 0)}")
        logging.info(f"📊 Inconsistent responses: {len(manager.inconsistent_responses)}")
        logging.info(f"📊 Manual review needed: {len(unified_results.get('manual_review_needed', {}))}")
        logging.info(f"📄 Results saved to: {output_file}")
        # Final KDF version log
        kdf_version = manager.get_kdf_version()
        if kdf_version:
            logging.info(f"Completed collecting responses from KDF version {kdf_version}")
        else:
            logging.info("Completed collecting responses (KDF version unknown)")
        
        # Update response files if requested
        if args.update_files:
            updated_count = manager.update_response_files(unified_results.get("auto_updatable", {}))
            logging.info(f"📄 Updated response files with {updated_count} new responses")
        
    except KeyboardInterrupt:
        logging.info("⚠️ Collection interrupted by user")
        manager.log_final_statistics()
        
    except Exception as e:
        logging.error(f"❌ Collection failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
