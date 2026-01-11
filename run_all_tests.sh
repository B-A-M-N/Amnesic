#!/bin/bash
echo "Running Amnesic Framework Verification Suite"
echo "============================================"

echo "1. Running Control Proofs (Base Baseline)"
python3 tests/control_proofs/control_basicsemantic_proof.py
if [ $? -ne 0 ]; then echo "Control Basic Proof Failed"; exit 1; fi

echo "   [1b] Control: Cognitive Load..."
python3 tests/control_proofs/control_cognitive_load.py
if [ $? -ne 0 ]; then echo "Control Cognitive Load Failed"; exit 1; fi

echo "   [1c] Control: Determinism..."
python3 tests/control_proofs/control_determinism.py
if [ $? -ne 0 ]; then echo "Control Determinism Failed"; exit 1; fi

echo "--------------------------------------------"
echo "2. Running Unit Tests (Step Verification)"
export PYTHONPATH=$PYTHONPATH:.
python3 tests/unit_tests/test_basic_semantic_steps.py
if [ $? -ne 0 ]; then echo "Basic Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_advanced_semantic_steps.py
if [ $? -ne 0 ]; then echo "Advanced Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_capabilities.py
if [ $? -ne 0 ]; then echo "Capabilities Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_persona_swap.py
if [ $? -ne 0 ]; then echo "Persona Swap Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_integration.py
if [ $? -ne 0 ]; then echo "Integration Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_langgraph.py
if [ $? -ne 0 ]; then echo "LangGraph Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_prefetch_unit.py
if [ $? -ne 0 ]; then echo "Prefetch Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_comparator_unit.py
if [ $? -ne 0 ]; then echo "Comparator Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_calculate_unit.py
if [ $? -ne 0 ]; then echo "Calculate Tool Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_determinism_unit.py
if [ $? -ne 0 ]; then echo "Determinism Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_cognitive_load_unit.py
if [ $? -ne 0 ]; then echo "Cognitive Load Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_contracts_unit.py
if [ $? -ne 0 ]; then echo "Contracts Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_ignorance_unit.py
if [ $? -ne 0 ]; then echo "Ignorance Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_presets_unit.py
if [ $? -ne 0 ]; then echo "Presets Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_code_engineering_unit.py
if [ $? -ne 0 ]; then echo "Code Engineering Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_hardening_unit.py
if [ $? -ne 0 ]; then echo "Hardening Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_module_construction.py
if [ $? -ne 0 ]; then echo "Module Construction Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_framework_diagnostics.py
if [ $? -ne 0 ]; then echo "Framework Diagnostics Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_prompt_safety.py
if [ $? -ne 0 ]; then echo "Prompt Safety Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_feasibility_unit.py
if [ $? -ne 0 ]; then echo "Feasibility Unit Tests Failed"; exit 1; fi
python3 tests/unit_tests/test_elastic_mode_unit.py
if [ $? -ne 0 ]; then echo "Elastic Mode Unit Tests Failed"; exit 1; fi

echo "--------------------------------------------"
echo "3. Running Basic Semantic Proof (Gold Standard)"
python3 tests/proofs/basic_semantic_proof.py
if [ $? -ne 0 ]; then echo "Semantic Proof Failed"; exit 1; fi

echo "--------------------------------------------"
echo "4. Running Advanced Semantic Proof (Logic Gate)"
python3 tests/proofs/advanced_semantic_proof.py
if [ $? -ne 0 ]; then echo "Advanced Proof Failed"; exit 1; fi

echo "--------------------------------------------"
echo "5. Running Capability Proofs (Externalized Cognition)"
echo "   [5a] Structural GC..."
python3 tests/proofs/proof_gc.py
if [ $? -ne 0 ]; then echo "GC Proof Failed"; exit 1; fi

echo "   [5b] Contract Enforcement..."
python3 tests/proofs/proof_contracts.py
if [ $? -ne 0 ]; then echo "Contract Proof Failed"; exit 1; fi

echo "   [5c] Failure Isolation..."
python3 tests/proofs/proof_isolation.py
if [ $? -ne 0 ]; then echo "Isolation Proof Failed"; exit 1; fi

echo "   [5d] Time Travel (Versioning)..."
python3 tests/proofs/proof_time_travel.py
if [ $? -ne 0 ]; then echo "Time Travel Proof Failed"; exit 1; fi

echo "   [5e] Hive Mind (Sync)..."
python3 tests/proofs/proof_hive_mind.py
if [ $? -ne 0 ]; then echo "Hive Mind Proof Failed"; exit 1; fi

echo "   [5f] Ignorance Detection..."
python3 tests/proofs/proof_ignorance.py
if [ $? -ne 0 ]; then echo "Ignorance Proof Failed"; exit 1; fi

echo "   [5g] Cognitive Load Shaping..."
python3 tests/proofs/proof_cognitive_load.py
if [ $? -ne 0 ]; then echo "Cognitive Load Proof Failed"; exit 1; fi

echo "   [5h] Determinism Levers..."
python3 tests/proofs/proof_determinism.py
if [ $? -ne 0 ]; then echo "Determinism Proof Failed"; exit 1; fi

echo "   [5i] Elastic Context Management..."
python3 tests/proofs/proof_elastic_context.py
if [ $? -ne 0 ]; then echo "Elastic Context Proof Failed"; exit 1; fi

echo "   [5j] Semantic Self-Correction..."
python3 tests/proofs/proof_self_correction.py
if [ $? -ne 0 ]; then echo "Self-Correction Proof Failed"; exit 1; fi

echo "   [5k] Marathon Session (Infinite Horizon)..."
python3 tests/proofs/proof_marathon.py
if [ $? -ne 0 ]; then echo "Marathon Proof Failed"; exit 1; fi

echo "   [5l] Extreme Efficiency (Micro-Kernel)..."
python3 tests/proofs/proof_extreme_efficiency.py
if [ $? -ne 0 ]; then echo "Efficiency Proof Failed"; exit 1; fi

echo "   [5m] Workspace Nexus (Multi-Repo)..."
python3 tests/proofs/proof_workspace_nexus.py
if [ $? -ne 0 ]; then echo "Nexus Proof Failed"; exit 1; fi

echo "   [5n] Cross-Model Invariance..."
python3 tests/proofs/proof_model_invariance.py
if [ $? -ne 0 ]; then echo "Invariance Proof Failed"; exit 1; fi

echo "   [5o] Failure Taxonomy (Safety)..."
python3 tests/proofs/proof_failure_taxonomy.py
if [ $? -ne 0 ]; then echo "Taxonomy Proof Failed"; exit 1; fi

echo "   [5p] Human-in-the-Loop Friction..."
python3 tests/proofs/proof_human_friction.py
if [ $? -ne 0 ]; then echo "Human Friction Proof Failed"; exit 1; fi

echo "--------------------------------------------"
echo "6. Running Code Engineering Proofs"
echo "   [6a] Basic Code Modification..."
python3 tests/proofs/proof_code_basic.py
if [ $? -ne 0 ]; then echo "Basic Code Proof Failed"; exit 1; fi

echo "   [6b] Advanced Multi-File Refactor..."
python3 tests/proofs/proof_code_advanced.py
if [ $? -ne 0 ]; then echo "Advanced Code Proof Failed"; exit 1; fi

echo "--------------------------------------------"
echo "7. Running Persona Swap Proof"
python3 tests/proofs/proof_persona_swap.py
if [ $? -ne 0 ]; then echo "Persona Swap Proof Failed"; exit 1; fi

echo "--------------------------------------------"
echo "8. Running Dual-Slot Comparator Proof"
python3 tests/proofs/proof_comparator.py
if [ $? -ne 0 ]; then echo "Comparator Proof Failed"; exit 1; fi

echo "--------------------------------------------"
echo "9. Running LRU Stress Test"
python3 tests/proofs/real_stress_test.py
if [ $? -ne 0 ]; then echo "Stress Test Failed"; exit 1; fi

echo "============================================"
echo "All Systems Nominal."