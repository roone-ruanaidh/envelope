# Inference as a tier in the computation hierarchy

**Research cutoff:** 2026-07-23

**Status:** unpromoted research; no experiment has been approved or run

**Purpose:** map how the relevant computer-science traditions relate, where their claims are established, where systems connect them, and where the connections remain untested

Read with the existing work on [recursive model control](recursive-language-model-control.md), the [Python REPL](python-repl-semantic-coprocessor.md), [durable acceptance-priced work](durable-invariant-acceptance-priced-work.md), and the [foundations research](FOUNDATIONS_RESEARCH_2026-07-10.md).

## How to read this report

This is not a novelty screen, product decision, or attempt to collapse the frame into one architecture. The existence of prior work has four uses here:

1. **Name the mechanism** so the research can inherit its definitions.
2. **Bound the claim** by separating what that work actually establishes from what is merely adjacent.
3. **Supply a baseline or instrument** instead of rebuilding it.
4. **Expose the seam** where two established mechanisms have not been studied together.

“Already exists” therefore never means “abandon it.” It usually means the component is available for studying a more interesting relation.

The report uses these evidence labels:

- **Formal:** proved relative to a stated mathematical or type-theoretic model.
- **Established mechanism:** mature semantics or a repeatedly implemented systems pattern.
- **Bounded empirical:** observed in named tasks, workloads, or studies; transfer is not implied.
- **Connected:** a published system directly joins two components of this frame.
- **Frontier:** a recent or preliminary attempt to push an edge.
- **Open edge:** the endpoints exist, but no direct evaluation of their proposed relation was found.
- **Unsupported bridge:** the endpoint facts do not imply the claimed connection.

“Proved” is reserved for formal results. A production implementation proves existence, not correctness, generality, or economic value.

## The picture

The brief is not one idea. It is a proposed intersection of five research lines:

```text
                         SOLVER SELECTION
              selective prediction / defer / route / cascade
                                      |
          L0 rule  <->  L1 specialist  <->  L2 general model  <->  human
              ^               ^                   |
              |               |                   |
         synthesize        distill              record
              \               |                   /
               +------ REPRESENTATION CHANGE ----+
                 cache / prompt / skill / weights / code
                                      |
                              ADMISSION AND AUTHORITY
                     contract / checker / proof / capability
                                      |
                              accepted state transition

       CONTROL SEMANTICS                                      HUMAN CONTINUITY
 condition -> recovery menu -> selection -> resume/replay     supervise / practice
                 |                     |                       govern / explain
                 +---- durable state --+------------------------------+
```

Most boxes are old. Several arrows are implemented in bounded systems. The research frontier is whether the arrows compose:

- Does the same recurring structure support routing, caching, specialist training, and deterministic compilation?
- Can a recovery choice mean the same thing in a live continuation and a durable replay?
- Can admission checks make downward movement between tiers safe without rejecting the useful cases?
- Can the system reduce routine human work while preserving the situated competence and rationale needed for rare cases?
- Can a mutable, inspectable system remain contained, reconstructible, and explainable?

The frame’s central conjecture is that these components may form a **longitudinal computation hierarchy**: experience changes where work is performed and how it is represented. That conjunction is not established.

### Relationship map at a glance

| Relation | Present state | What is known | What remains open |
|---|---|---|---|
| Input → cheapest competent solver | Formal foundations + bounded empirical systems | Selective prediction, learning to defer, routing, and cascades can improve a risk–cost frontier under their assumptions | Open-ended, stateful, drifting judgment workloads |
| Repeated query → response reuse | Connected and implemented | Semantic caches can reduce calls when an equivalence policy is calibrated | Safe equivalence under context, action, and policy drift |
| Recurring domain → smaller specialist | Bounded empirical | Narrow supervision, retrieval, or tuning can let small systems beat larger general models on selected tasks | General data/lift curve; annotation amortization; longitudinal stability |
| Expensive outputs → cheaper learned expert | Connected in bounded settings | Distillation and online cascade learning transfer some behavior | Correlated teacher error, rationale loss, recalibration, rollback |
| Experience → executable skill | Connected frontier | Curated skills often help; validated skills can accumulate | Autonomous construction, composition, scope, retirement |
| Experience → deterministic rule/code | Mature ancestors + frontier agent systems | Rule extraction and program synthesis can compile behavior on bounded domains | Choosing when this representation is valid and preserving intensional knowledge |
| Condition → named recovery alternatives | Established language mechanism | Common Lisp and Dylan dynamically advertise application-specific recovery alternatives | Typed, machine-readable contracts suitable for model selection |
| Recovery choice → live control transfer/resumption | Established, with different semantics | Common Lisp transfers to a named restart clause; Smalltalk can resume/retry; effect handlers can resume a captured delimited continuation | Which semantics real inference workloads need instead of ordinary branch/rerun |
| Recovery choice → crash-durable resumption | Connected at workflow granularity | Durable engines journal effects, pause for signals, and replay | Faithful correspondence with fine-grained live recovery |
| Model proposal → formal admission | Established ancestry + emerging agent coupling | Contracts, refinement types, PCC, runtime policy monitors; recent agent gates | Specification adequacy, external facts, cost, useful semantic coverage |
| Admission → safe tier demotion | Open edge | A checker can bound encoded errors | Whether useful demotion is possible at tolerable false-accept and false-reject rates |
| External state → persistent context/execution continuity | Connected | RLMs and durable workflows externalize context and execution history | Whether continuity becomes durable integrated competence or “theory” |
| Automation/nonuse → competence risk; promotion-specific edge | General mechanism established; promotion edge open | Nonuse and out-of-loop automation can degrade skill or situation awareness | Magnitude, timescale, and counter-practice in agentic knowledge work |
| Ambient visibility → supervisory performance | Mature design tradition; tier relation open | Supervisory control, ecological interfaces, direct manipulation, spreadsheets supply design vocabularies | Effect on detection, takeover, attention, and retained competence |
| Guest-local freedom + attenuated outward authority | Components implemented; hybrid conjunction open | MicroVMs provide containment; capability systems attenuate authority | Security semantics, confused-deputy resistance, and usable mutable-agent design |
| Live image → reproducible, theory-preserving system | Components exist; conjunction open | Snapshots, event logs, builds, migrations, and rationale records solve different parts | A system joining them across code/model/schema evolution |
| Formal language properties ↔ model fluency | Both axes empirically real | Substrate semantics matter; training distribution can be moved | Their exchange rate for recovery and proof tasks |
| Interaction-net confluence → HVM speculative recovery | Unsupported bridge + frontier implementation question | Lafont-style systems can be strongly confluent; HVM exposes sharing constructs | Preservation in concrete HVM runtimes; recovery selection, effects, persistence, measured advantage |

## 1. “Locality” is several different hypotheses

The memory-hierarchy analogy is useful only after its overloaded word—*locality*—is split apart.

### 1.1 Primitive workload properties

The primitive properties must be measured separately before they are combined into mechanism-specific “localities”:

| Property | Empirical question |
|---|---|
| **Incidence concentration** | How much volume is covered by the top ambiguity families? |
| **Query recurrence** | How often do equal or similar inputs recur? |
| **Resolution equivalence** | Under what state, time, and policy conditions may one resolution substitute for another? |
| **Competence predictability** | Do observable features predict which solver will be acceptable at lowest total cost? |
| **Specialist generalizability** | Does a bounded subdistribution support a cheaper learned expert on future cases? |
| **Rule expressibility and stability** | Is the relation expressible as deterministic code with a checkable scope, and does that scope remain stable? |
| **Control dependency** | Does a resolution change which computation becomes reachable next, or can cases be collected and resolved in a batch? |

Mechanisms require different combinations:

| Mechanism | Required evidence |
|---|---|
| Pre-routing/cascading | Competence predictability and positive conditional net value |
| Response caching | Query recurrence plus resolution equivalence |
| Specialist training | Enough incidence plus future-split generalizability |
| Rule/code extraction | Expressibility, scope evidence, and stability |
| Batch resolution | Independence rather than locality |

These quantities may correlate, but none implies another. A workload can have:

- a flat ambiguity taxonomy and still route well because the cheapest solver is predictable;
- repeated queries and still be unsafe to cache because context changes the valid resolution;
- concentrated demand that does not support a specialist because the top category is internally heterogeneous;
- a strong specialist that cannot be compiled into a rule;
- stable rules for rare cases that have no incidence concentration;
- highly sequential decisions without any reusable answer.

The original E0 histogram could test incidence concentration only. It could not answer the routing or caching questions, because routing needs **competence predictability**, while caching needs **resolution equivalence**. Search-query locality and semantic-cache studies establish recurrence for particular workloads; routing benchmarks establish complementarity and partial competence predictability. Neither establishes a general “working set of judgment.”

### 1.2 The central relational hypothesis

The partitions need not be identical. One history can support several mechanisms through partial mappings:

```text
resolution-equivalence class --predicts?--> cheapest competent solver
             |                                  |
             +--supports?--> specialist region  |
             +--contains?--> stable rule scope <-+
```

The empirical center is the **cross-predictability, overlap, and transfer value** among these partitions, including pairwise relations and counterexamples. An ambiguity cluster might predict a specialist without licensing response reuse; a cache-equivalence class might span several solver regions; a rule may cover only a strict subset of a learned specialist’s domain.

No reviewed work measures this relation longitudinally across all representation paths. Exact four-way alignment is neither required nor expected.

Memory systems have exact addresses and correctness-preserving movement of bytes. Semantic systems infer both the address and the equivalence class. Their “cache controller” is therefore part router, part learner, part verifier, and part policy. That is the important disanalogy—not a reason to discard the analogy, but the source of its research questions.

## 2. Solver selection: a mature lineage with an open systems extension

Tier selection sits in a long line:

- Chow’s reject-option theory formalized error/rejection tradeoffs in 1970. [Chow](https://doi.org/10.1109/TIT.1970.1054406)
- Adaptive mixtures of local experts learned both local predictors and a gating network. [Jacobs et al.](https://www.cs.toronto.edu/~hinton/absps/jacobs.pdf)
- The Viola–Jones cascade arranged increasingly expensive classifiers so early stages cheaply reject most cases. [Viola and Jones](https://mlanthology.org/cvpr/2001/viola2001cvpr-rapid/)
- Conditional computation learned to activate only part of a network. [Bengio et al.](https://arxiv.org/abs/1308.3432)
- Learning to defer generalized abstention to a fallible human or other expert; later work extends this to multiple experts. [Mozannar and Sontag](https://proceedings.mlr.press/v119/mozannar20b.html), [Verma et al.](https://proceedings.mlr.press/v206/verma23a.html)
- FrugalGPT, RouteLLM, and unified routing/cascading apply the same structure to language models. [FrugalGPT](https://arxiv.org/abs/2305.05176), [RouteLLM](https://arxiv.org/abs/2406.18665), [Unified Routing and Cascading](https://arxiv.org/abs/2410.10347)

### What is established

Within specified supervised decision problems, selective predictors and deferral objectives have formal risk properties or consistent estimators. Within bounded language-model benchmarks, routers and cascades can exploit complementary models and move a measured cost–quality frontier.

LLMRouterBench’s 400K-plus examples, 21 datasets, 33 models, and 10 routing baselines show both sides of the current state: models are complementary enough to create a large oracle opportunity, while many learned routers fail to beat simple baselines. Within that benchmark’s model pool, datasets, router families, and oracle definition, persistent model-recall failures leave much of the opportunity unrealized. [LLMRouterBench](https://aclanthology.org/2026.findings-acl.1881/)

A 2026 preprint comparing deterministic threshold cascades across five datasets and eight models found longer fixed chains often inferior to the pairwise envelope and a lightweight pre-router best on four of five datasets. That is useful boundary evidence about one cost geometry: every failed lower-tier call is sunk cost. It does not show that cascades generally fail, particularly when L0/L1 are nearly free or their output determines subsequent control flow. [Is Escalation Worth It?](https://arxiv.org/abs/2605.06350)

### What is not established

The existing results do not establish:

- reliable routing for open-ended semantic state transitions;
- stability when solvers, prompts, tools, data, and policy all change;
- a hierarchy whose lower tiers learn from the higher tiers over time;
- end-to-end cost once verification, rejected calls, labels, retraining, human attention, and false acceptance are counted;
- a linear ordering of experts. Multi-expert deferral permits competence regions that cross rather than form a simple ladder;
- that a human is appropriately represented as the last and most expensive solver.

These results give the **selection component** established names and strong baselines. Its longitudinal and stateful relations remain open.

### 2.1 The L1 tier is a family, not one empirical result

“Domain-tagged open-weight model” combines interventions that the literature usually studies separately:

| Intervention | What changes |
|---|---|
| Domain/task tag | Router input or conditioning signal |
| Expert-authored label | Ground truth or supervision |
| Teacher-generated label/rationale | Distillation data |
| Domain corpus | Pretraining or fine-tuning distribution |
| Retrieval/index | Information available at inference |
| Tool or procedural package | Action space and operational knowledge |

There is good bounded evidence for the broader proposition: a small specialized system can match or beat a much larger general model on a narrow task.

- A Bank of England study across 17 sentence-classification tasks found penalized logistic regression over embeddings from a small local model often matched or exceeded large-model classifiers with dozens of labels per class. [Bank of England](https://www.bankofengland.co.uk/working-paper/2025/improving-text-classification-logistic-regression-llms-tens-of-shot-classifiers)
- Fine-tuned FinBERT/FinDRoBERTa variants can outperform GPT-3.5/4 zero-shot results on selected financial-sentiment data. [Compact Models for Financial Sentiment](https://arxiv.org/abs/2409.11408)
- Distilling step-by-step showed a 770M student using teacher rationales outperforming much larger few-shot models on selected benchmarks. [Hsieh et al.](https://aclanthology.org/2023.findings-acl.507/)
- Laboratory-scale fine-tuning reports 7B models competitive with GPT-4-Turbo on selected social-science tasks. [Laboratory-Scale AI](https://arxiv.org/abs/2405.16820)

The evidence is not a general “expert tagging beats frontier inference” law. FinNLI shows substantial domain-shift failures and weak results from some finance instruction-tuned models. [FinNLI](https://aclanthology.org/2025.findings-naacl.257/) FinRAG-12B mixes filtered public, synthetic, and proprietary banking data rather than isolating expert tags. [FinRAG-12B](https://arxiv.org/abs/2605.05482) The rLLM-FinQA-4B artifact reports a strong small tool-using agent result, but it is a project result, not evidence for a general tagging mechanism. [rLLM-FinQA-4B](https://huggingface.co/rLLM/rLLM-FinQA-4B)

The open questions are causal and economic:

- Which gain came from labels, tags, retrieval, tools, data quality, training recipe, or evaluation match?
- What is the label-count/lift curve by task family?
- When should L1 be a classifier, retriever, symbolic solver, or rule instead of a generator?
- Do expert-authored ambiguity taxonomies help beyond learned input features?
- How quickly does the specialist’s competence region drift?
- Does its avoided acceptance cost repay annotation, training, hosting, calibration, and review?

This is a research program, not a reason to remove L1 from the frame.

### 2.2 Cost-to-acceptance is not cost-to-success

Risk–coverage work prices abstention against error. Routing work traces empirical cost–quality frontiers. Cost-of-Pass estimates inference price per oracle-known correct solution. [Cost-of-Pass](https://arxiv.org/abs/2504.13359) None alone supplies the brief’s longitudinal quantity.

Do not force acceptance and correctness into one denominator. Report at least:

- **cost per admitted transition,** whether or not the transition is independently correct;
- **correctness/risk among admitted transitions** at each coverage level;
- **cost per oracle-known correct transition,** when an independent oracle exists;
- **false-accept loss,** including downstream remediation;
- the component costs of routing, attempted inference, verification, escalation delay, labels, amortized training, cache invalidation, and human attention.

“AI Agents That Matter” similarly argues that cost and reproducibility belong in evaluation rather than beside it. [Kapoor et al.](https://arxiv.org/abs/2407.01502)

No reviewed source establishes one generally valid cost-to-acceptance model. Building the measurement is itself useful infrastructure.

## 3. Reuse and promotion: four distinct representation changes

The proposed L2 → L1 → L0 path intersects mature work, but “promotion” is not one operation.

| Destination | What is retained | Existing line | Primary risk |
|---|---|---|---|
| **Response cache** | Instance-level answer or resolution | Exact/semantic caching | Equivalence and context drift |
| **Prompt or skill** | Explicit procedure, resources, examples | Voyager, SkillsBench, SkillFoundry | Retrieval, composition, stale assumptions |
| **Student/specialist weights** | Generalized behavior | Knowledge distillation, online cascade learning | Teacher error, opaque divergence, calibration |
| **Rule or code** | Deterministic procedure | Rule extraction, program synthesis | Specification error, narrow scope, hidden rationale |

### 3.1 Response caching: where the memory analogy is literal

GPTCache and SCALM implement semantic response reuse. [GPTCache](https://aclanthology.org/2023.nlposs-1.24/), [SCALM](https://arxiv.org/abs/2406.00025) vCache/VectorQ learns per-prompt adaptive equivalence thresholds and evaluates error-bound calibration in its model and benchmarks. [vCache](https://arxiv.org/abs/2502.03771), [implementation](https://github.com/vcache-project/vCache)

Krites is especially close to the frame: a vetted static cache serves clear matches, while grey-zone misses are judged asynchronously and, if accepted, promoted into a dynamic cache. Its trace simulation reports increased cache coverage, but uses a benchmark equivalence oracle rather than a deployed LLM judge in the evaluation loop. [Krites](https://arxiv.org/abs/2602.13165)

Recent evaluation across 74,265 queries, nine retrievers, and ten rerankers finds a calibration gap between ranking quality and deployment threshold quality. [Semantic-cache calibration](https://arxiv.org/abs/2606.19719) This is precisely the disanalogy from hardware: embedding proximity does not establish semantic substitutability.

These systems connect different parts of the edge. GPTCache/SCALM establish semantic reuse; vCache studies statistically bounded cache admission under its assumptions; Krites studies asynchronous judged promotion while substituting benchmark equivalence classes for the deployed judge in its principal trace evaluation. None establishes that cached actions remain valid under changed state, permissions, policy, or time.

### 3.2 Distillation: behavior moves, not necessarily theory

Online Cascade Learning collects LLM demonstrations, trains cheaper stream classifiers, and learns when to defer. It reports no-regret analysis and large cost reductions across four benchmarks. This directly connects higher-tier outputs to a learned lower tier in a bounded setting. [Online Cascade Learning](https://proceedings.mlr.press/v235/nie24a.html)

Knowledge-distillation research also warns against describing this as faithful transfer. Students can diverge substantially from teacher output distributions depending on data and temperature. [Does Knowledge Distillation Really Work?](https://research.google/pubs/does-knowledge-distillation-really-work/) A student may preserve decisions on the evaluated support while losing calibration, rationale, or behavior under perturbation.

Thus L2 → L1 is implemented as behavior transfer. General semantic-judgment promotion with provenance, future-split validation, drift detection, and reversible rollback remains open.

### 3.3 Skills: executable accretion exists; autonomous compounding is frontier

Voyager stores validated code from successful Minecraft interactions in a reusable skill library. [Voyager](https://arxiv.org/abs/2305.16291) SkillsBench v4 reports a 16.6 percentage-point mean improvement from curated skills across 87 tasks. It also reports no average benefit from one-shot self-generated skills in the evaluated configurations. [SkillsBench v4](https://arxiv.org/abs/2602.12670v4) SkillFoundry pushes further by mining and testing reusable scientific skills in a closed loop. [SkillFoundry](https://arxiv.org/abs/2604.03964)

Newer preprints split autonomous learning further. SkillLearnBench evaluates one-shot, self/teacher-feedback, and skill-creator methods over 20 verified tasks: all beat no-skill on average, no method leads across tasks/models, iterative external feedback helps, and self-feedback alone exhibits recursive drift. [SkillLearnBench](https://arxiv.org/abs/2604.20087) SkillEvolver reports iterative deploy–evaluate–refine gains with a fresh-agent overfit audit across 83 SkillsBench tasks and three kernel tasks. [SkillEvolver](https://arxiv.org/abs/2605.10500)

These results establish that explicit executable procedure can improve agent performance and can accumulate. They separate one-shot synthesis, trajectory-conditioned refinement, external-feedback selection, and autonomous lifecycle management; no one result establishes all four. Skill selection, scope, composition, permissions, provenance, version drift, correlated errors, and retirement remain active boundaries.

“Executable ontology” should also be decomposed:

```text
ontology             vocabulary, relations, invariants
rules / planner      derived facts or legal action sequences
skill / code         operational transition
verifier             admission of its result
```

OWL axioms, Datalog rules, PDDL action models, agent skills, and executable code are related but different artifacts. [OWL 2](https://www.w3.org/TR/owl2-syntax/), [PDDL resources](https://ipc08.icaps-conference.org/deterministic/PddlResources.html) Calling all of them “knowledge as code” obscures what is declarative, executable, checkable, and state-changing.

### 3.4 Rule extraction: L2 → L0 has deep ancestors

TREPAN extracted symbolic decision trees from neural networks in 1995. [TREPAN](https://proceedings.neurips.cc/paper/1995/hash/45f31d16b1058d586fc3be7207b58053-Abstract.html) VIPER distilled neural policies into verifiable decision trees for bounded reinforcement-learning cases. [VIPER](https://papers.neurips.cc/paper/7516-verifiable-reinforcement-learning-via-policy-extraction) Inductive synthesis has long combined examples with invariant enforcement. [Program synthesis with invariants](https://arxiv.org/abs/1907.07273) RuleChef is a recent LLM-assisted system that learns and repairs rules from labels, feedback, or observed model behavior. [RuleChef](https://arxiv.org/abs/2607.01293)

The new boundary is not whether learned behavior can ever become a rule. It is whether one longitudinal escalation history can safely choose among cache, skill, model, and rule representations while retaining:

- the scope in which the artifact was supported;
- counterexamples and rejected alternatives;
- the reason for the transition;
- future-split and drift evidence;
- a rollback path;
- the human practice needed to supervise the remaining cases.

Some promotion paths behave as **lossy compilation**. A student or rule may preserve extensional behavior on observed cases while losing calibration, rationale, similarity judgments, assumptions, or alternatives. Cache insertion is reuse rather than compilation but can lose the context that made substitution valid; a skill may add explicit procedure while still omitting scope or provenance. The information loss must be characterized per representation.

## 4. Control direction: model-on-top and code-on-top are both active

The claim that model-driven harnesses dominate is directionally useful, but code-on-top systems already exist.

- RLMs put context in an external environment and let a model recursively inspect and transform it. [RLM](https://arxiv.org/abs/2512.24601)
- Recursive Agent Harnesses run many independent model invocations over decomposed entries; their Oolong evaluation demonstrates scalable model-on-top decomposition, not sequential resumption. [RAH](https://arxiv.org/abs/2606.13643)
- CodeAct has the model emit executable Python actions and revise them through environment feedback. Its 17-model evaluation is a strong model-on-top code-action baseline, not a test of code-owned escalation. [CodeAct](https://arxiv.org/abs/2402.01030)
- BINDER lets generated code call models for unresolved table operations. [BINDER](https://arxiv.org/abs/2210.02875)
- LOTUS exposes declarative model-backed semantic operators and proxy/oracle cascades. [LOTUS](https://arxiv.org/abs/2407.11418)
- lambda-RLM describes its combinators as typed and pre-verified; its formal results concern termination, cost, and accuracy under size-decreasing decomposition and simplified models, not a general type-safety or combinator-verification proof. [lambda-RLM](https://arxiv.org/abs/2603.20105)
- “LLM-as-Code” explicitly studies a program-owned control flow with models as adaptive components, though its evidence is a case study. [LLM-as-Code](https://arxiv.org/abs/2606.15874)

C1 is also part of an explicit 2026 research agenda. The *Code as Agent Harness* survey organizes code as interface, control/memory mechanism, and shared multi-agent substrate; *AI Harness Engineering* proposes trace-based evaluation of eleven runtime responsibilities but validates only one controlled task. They map the emerging field and its open problems rather than establishing a winning control direction. [Code as Agent Harness](https://arxiv.org/abs/2605.18747), [AI Harness Engineering](https://arxiv.org/abs/2605.13357)

C1 is therefore a **connected research line**. Its open relation is bidirectional composition: deterministic execution, model escalation at a semantically meaningful boundary, checked resolution, and resumption into the same computation—measured against batch, rerun, and model-driven baselines.

The sequential-dependency question remains decisive for that edge. If resolutions are independent, collect–resolve–rerun may dominate. If a resolution changes later reachable work, immediate continuation can express a different computation. Existing independent-entry harness results do not answer how often the latter occurs in real workloads.

## 5. Restarts are four mechanisms, not one

C2 bundles four orthogonal axes:

1. **Recovery vocabulary:** what alternatives are available?
2. **Policy selection:** which program, model, or human chooses?
3. **Control resumption:** continue a live frame, retry, branch, or replay?
4. **Persistence and admission:** what survives failure, and what is permitted?

Each axis has substantial prior art. Their integration is the open research object.

### 5.1 Conditions and restarts

Common Lisp separates:

- the **signaler**, which detects that it cannot proceed;
- the **recovery provider**, which establishes named restarts;
- the **handler**, which supplies policy;
- the debugger/human, which can act as handler of last resort.

Handlers installed with `handler-bind` are invoked before automatic unwinding, so dynamically available recovery actions remain discoverable. Invoking a typical `restart-case` restart then transfers control to its recovery clause and unwinds to the restart establishment point; it does not inherently resume at the signaling expression. `handler-case` clauses likewise run after control transfer rather than in the original signaling context. Pitman calls restarts effectively named continuations, but the control behavior is narrower than a general first-class continuation. More strikingly, he proposed handlers producing sets of possible actions annotated with motivations, consequences, and qualitative goodness, combining advice, then seeking confirmation. That is already a conceptual design for multiple reasoners proposing and selecting recovery. [Pitman, *Condition Handling in the Lisp Language Family*](https://www.nhplace.com/kent/Papers/Condition-Handling-2001.html), [CLHS ch. 9](https://clhs.lisp.se/Body/09_a.htm)

Smalltalk supplies resumable exception actions such as `resume:`, `retry`, `retryUsing:`, `pass`, and `outer`. [GNU Smalltalk](https://www.gnu.org/software/smalltalk/manual/html_node/Handling-exceptions.html) Dylan defines a documented **recovery protocol** specifying permitted return behavior, expected restart handlers, and restart arguments, while explicitly lacking a formal mechanism for expressing the protocol. [Dylan DRM](https://opendylan.org/books/drm/Exception_Handling)

The historical mechanism is therefore closer to the brief than “debugger as human oracle” alone. What general inference changes is the feasible policy selector and the economics of invoking it.

### 5.2 Algebraic effects are adjacent, not equivalent

| Condition-system feature | Algebraic-effects relation |
|---|---|
| Condition payload | Roughly analogous to an effect operation payload |
| Dynamic `handler-bind` search | Related to nested handler forwarding |
| Restart invocation | Usually transfers to a declared recovery clause; not inherently continuation resumption |
| Effect-handler resumption | Explicitly resumes the captured delimited continuation; no inherent named restart menu |
| Human-facing description/query protocol | Not inherent to effect semantics |

Effect handlers provide typed operation signatures and explicit delimited continuations. They may resume zero, one, or multiple times. Common Lisp emphasizes protocol negotiation among separately developed components: one layer signals, another offers recovery, another chooses.

Calling algebraic effects “the condition system formalized” is therefore an unsupported identity. The relation is productive precisely because each supplies something the other does not. [Plotkin and Pretnar](https://arxiv.org/abs/1312.1399), [Eff](https://arxiv.org/abs/1203.1539), [Frank](https://arxiv.org/abs/1611.09259), [Koka](https://koka-lang.github.io/koka/doc/book.html), [OCaml 5](https://ocaml.org/manual/5.3/effects.html)

OCaml 5 gives typed effect-operation payload/results and dynamically enforced one-shot continuation use; its function types do not track performed effects. Koka and Racket can demonstrate multi-shot resumption in pure computation. Once continuations capture mutable state, open resources, or external effects, speculative branching requires linearity, isolation, rollback, or effect-specific discipline.

### 5.3 Python generators expose the protocol boundary

PEP 342 gives explicit suspension, `.send(value)`, `.throw()`, and one live path through a generator. [PEP 342](https://peps.python.org/pep-0342/) It does not let an ordinary callee suspend through arbitrary callers: every intervening layer must cooperate or delegate. The standard generator protocol supplies neither cloning nor serialization; CPython generators are not pickleable. [Python issue 39817](https://bugs.python.org/issue39817)

Multiple named choices can be encoded as tagged messages, but that is a condition protocol built **above** generators. Python remains useful as an accessible model-facing harness and as an experiment in explicit recovery APIs. It is not a general resumable-control substrate.

### 5.4 Live continuations and durable replay solve different problems

Racket’s stateless servlet language obtains serializable continuations by transforming source into administrative normal form, making continuations explicit, and defunctionalizing functions into serializable data. It is constrained by serializable captured values, transformed-module boundaries, parameterization, and code-version compatibility. [Racket stateless servlets](https://docs.racket-lang.org/web-server/stateless.html)

Temporal-class durable engines instead re-execute deterministic workflow code from journaled history and substitute previously recorded operation results until they reach incomplete work. Nondeterminism, external effects, and durable waits must cross declared journaled operations, while ordinary local variables may be reconstructed during replay. Restate applies this pattern to model calls and durable human approval: nondeterministic calls are wrapped and journaled; completed results are replayed rather than called again; workflows can suspend on durable promises. [Temporal deterministic constraints](https://docs.temporal.io/workflow-definition#deterministic-constraints), [Temporal Activities](https://docs.temporal.io/activities), [Restate durable steps](https://docs.restate.dev/develop/python/durable-steps), [Restate durable agents](https://docs.restate.dev/ai/patterns/durable-agents), [Restate human approval](https://docs.restate.dev/ai/patterns/human-in-the-loop)

DBOS, Inngest, Azure Durable Functions/Agents, and Conductor expose related deployed couplings. [DBOS](https://docs.dbos.dev/integrations/vercel-ai), [Inngest](https://www.inngest.com/docs/learn/durable-agents), [Azure durable orchestration replay](https://learn.microsoft.com/en-us/azure/durable-task/common/durable-task-orchestrations), [Conductor HITL](https://docs.conductor-oss.org/devguide/ai/human-in-the-loop.html)

| Live continuation | Durable workflow |
|---|---|
| Retains dynamic context in memory | Reconstructs from code plus history |
| Can expose an inner frame’s implicit state | Reconstructs locals but journals effects and waits only at declared boundaries |
| May keep process resources live | Must externalize and reacquire resources |
| Resumes with low latency | Survives process or machine death |
| Has native-stack/code-layout coupling | Has deterministic-replay/version coupling |

Durable workflows already implement “model call as recorded nondeterministic effect” at explicit boundaries. They do not persist arbitrary native stacks. External calls also retain an acknowledgement gap: provider success before journal commit can cause duplicate work unless the effect has an idempotency key or compensation.

The open edge is a semantic correspondence:

> Can one typed, dynamically enumerated recovery protocol compile faithfully to both in-memory continuation semantics and event-sourced durable replay?

That requires specifying capture extent, one- versus multi-shot use, persistence, relocation/version compatibility, and external-effect safety. No mainstream candidate supplies all five without restrictions.

## 6. Admissibility: old foundations, new coupling

Admissibility belongs to established lines:

- Hoare logic, contracts, typestate, and refinement types;
- runtime security automata; [Schneider](https://ecommons.cornell.edu/items/73f44364-f45e-40b5-b581-301a42619b0d)
- proof-carrying code; [Necula and Lee](https://personal.utdallas.edu/~hamlen/Papers/necula96.pdf)
- proof-carrying plans; [Hill et al.](https://arxiv.org/abs/2008.04165)
- theorem-checked code and proofs in Lean, F*, Dafny, and related systems. [Lean proof validation](https://lean-lang.org/doc/reference/latest/ValidatingProofs/), [F*](https://fstar-lang.org/), [Dafny](https://dafny.org/dafny/DafnyRef/DafnyRef)

The generative connection is:

```text
Dylan-style recovery protocol
        + typed effect signature
        + pre/postcondition over state
        + checked evidence
```

A restart contract could expose:

```text
Restart {
  argument type
  state precondition
  transition semantics
  state postcondition
}
```

Compile-time and runtime gates are not a strict fork, but different certificate types must remain distinct:

- **Static verification** proves all executions of generated code satisfy an encoded contract under a model.
- **Runtime value checking** evaluates a proposed transition against current state and facts.
- **Formal proof-carrying value or plan** attaches a theorem-checker-readable witness of an encoded pre/postcondition.
- **Evidence/attestation envelope** attaches approvals, assumptions, receipts, and replay evidence without constituting a theorem that the transition satisfies a formal predicate.
- **Hybrid verification** statically checks the transition kernel and dynamically checks current facts plus a small certificate.

Recent work connects formal policy and agent actions, but remains frontier evidence:

- Agent-C translates temporal policies into formulas checked during tool-call generation. [Agent-C](https://arxiv.org/abs/2512.23738)
- Proof-Carrying Agent Actions proposes portable evidence envelopes containing approvals, assumptions, receipts, and replay material; its “proof” is a governance/audit certificate, not a theorem-prover proof. [PCAA](https://arxiv.org/abs/2606.04104)
- Runtime Compliance Verification/C-Trace instruments agent traces against policies. [C-Trace](https://arxiv.org/abs/2606.19242)
- GraphFlow proposes compile-time workflow contracts plus a durable runtime event log. [GraphFlow](https://arxiv.org/abs/2605.14968)

These works push the coupling; they do not establish general semantic safety. A type or proof establishes only the proposition actually encoded. It does not establish that the specification captures the domain, that external facts are current, or that an accepted transition is desirable.

The key research relation is not “formal proof versus schema.” It is **coverage versus burden**:

- Which false actions does each gate catch?
- Which valid actions does it reject?
- What does the specification cost to author and maintain?
- Does it remain true under model, policy, and world change?
- Does it provide enough coverage to permit cheaper-tier outputs without increasing false acceptance?

This is how admissibility might make tier demotion safe. That “might” is the open edge.

## 7. State, theory, and the mutable image

### 7.1 External state is established; integrated understanding is not

RLMs demonstrate that model context can remain in an external environment rather than being copied wholesale into a prompt. Durable workflows establish the same pattern for execution history. Databases, event sourcing, and content-addressed stores already externalize domain state.

C3 is therefore a strong systems pattern:

> Treat a model invocation as ephemeral computation over durable, inspectable external state.

What does not follow is that all relevant state has thereby become knowledge or theory. Persistence makes information available across time; it does not establish that the system integrates the reasons, recognizes relevant similarities, or adapts correctly under novel change.

### 7.2 Naur names a capability, not a theorem of model impossibility

Naur’s “theory” is the programmer’s ability to explain why a program has its form, answer questions, recognize similarity, and modify it for new circumstances. Code and documentation are secondary expressions. [Naur, *Programming as Theory Building*](https://ingenieria-de-software-i.github.io/assets/bibliografia/programming-as-theory-building.pdf)

This is a philosophical and case-based account, not a formal impossibility theorem. “A model holds theory” also extends a term Naur defined around human understanding. The claim can be decomposed into:

1. **Persistence:** are relevant facts and history available across time? C3 attacks this.
2. **Epistemic integration:** can the system use reasons and similarity judgments under novel changes? A revised E9 can test this behaviorally.
3. **Accountability, stake, and meaning:** who bears consequences and for whom does the work matter? This is normative or philosophical; a behavioral benchmark does not settle it.

Design-rationale systems already externalize more than admissibility: QOC and gIBIS record questions, options, criteria, argument, and tradeoffs. [QOC](https://doi.org/10.1080/07370024.1991.9667168), [gIBIS](https://www.gerrystahl.net/teaching/winter12/Conklin_gIBIS.pdf) Documented adoption problems include the cost of capturing and using rationale, not an absence of representational schemes. [Architecture-rationale survey](https://www.sciencedirect.com/science/article/pii/S0164121206001415)

A 2026 ACM evaluation gave five 2023–24-era models an architecture problem and chosen decision across 100 cases, then compared their generated arguments with human-listed rationale. It found useful but weak and inconsistent argument recovery: reported precision around .267–.278, recall .627–.715, and F1 .351–.389, with both helpful novel arguments and some misleading ones. [Shahab et al.](https://doi.org/10.1145/3785010), [preprint](https://arxiv.org/abs/2504.20781) This is adjacent frontier evidence, not a test of current frontier models reconstructing theory from a codebase.

Promotion should therefore measure:

- **extensional preservation:** behavior remains correct on observed cases and declared held-out or time-split perturbations;
- **intensional preservation:** constraints, alternatives, rationale, and similarity judgments survive;
- **provenance:** the causal history and evidence remain inspectable.

Admissibility records allowed boundaries. Rationale records alternatives and tradeoffs. Event logs record transition history. Active practice may maintain situated application and competence. None alone is “the theory.”

### 7.3 A live image combines four independent properties

“Image rot” should be split into measurable failures:

1. **Dependency/environment rot:** can declared software be rebuilt?
2. **State/schema drift:** can live state be migrated and interpreted?
3. **Causal opacity:** can we reconstruct how the state arrived here?
4. **Theory/ownership loss:** can someone explain and adapt why it has this form?

KeyKOS combined a persistent single-level store, system-wide checkpointing, capability security, and process resumption across power loss. [KeyKOS](https://pdos.csail.mit.edu/6.828/2010/readings/keykos.pdf) EROS implemented transparent persistence and capability protection on commodity x86 with periodic consistent snapshots. [EROS](https://www.princeton.edu/~rblee/ELE572Papers/Fall04Readings/Eros.pdf) Typed image-based programming research explores structured version control and schema migration for Smalltalk/Lisp/HyperCard/spreadsheet-like systems. [Edwards and Petricek](https://tomasp.net/academic/papers/typed-image/typed-image.pdf) Nix reconstructs declared immutable components but does not reproduce mutable state. [Dolstra](https://edolstra.github.io/pubs/phd-thesis.pdf)

A snapshot is recovery evidence, not provenance or theory. A build recipe reconstructs static inputs, not a live history. An event log records transition order, declared inputs, and receipts; it does not by itself explain causation or why choices were made. A rationale record does not guarantee executable consistency.

The frontier conjunction is:

```text
reproducible immutable base
  + versioned event/mutation log
  + schema migrations
  + periodic snapshots
  + admissibility evidence
  + rationale and provenance
```

Pieces exist. No reviewed source established that whole combination across live code, data, model, and runtime evolution.

## 8. One box, one wall: four boundaries inside one deployment

The literal claim “root in one box, no internal checks” is not supported by the security systems cited as analogues.

- Firecracker assumes guest code may be malicious and layers KVM, seccomp, namespaces/cgroups, and a jailer. It does not provide guest egress filtering; host policy must do so. [Firecracker design](https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md)
- gVisor interposes a user-space kernel and layers isolation; it explicitly does not replace secure architecture or external network/resource policy. [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/)
- KeyKOS/EROS authorize actions through possession of unforgeable capabilities.
- Capsicum brings capability mode and rights-limited descriptors to Unix. [Capsicum](https://research.google/pubs/capsicum-practical-capabilities-for-unix/)
- WASI distinguishes capabilities granted at linkage/runtime and supports attenuation, though implementations must be evaluated separately as security mechanisms. [WASI capabilities](https://github.com/WebAssembly/WASI/blob/main/docs/Capabilities.md), [WASI releases](https://wasi.dev/releases/)

The relational decomposition is:

1. **Containment boundary:** what can compromise the host?
2. **Authority boundary:** which files, networks, models, and durable state can the guest affect?
3. **Transition-integrity boundary:** which proposed changes may commit?
4. **Recovery boundary:** what can be rolled back or reconstructed?

One machine can contain all four, but they are not one wall. A proposed hybrid gives an agent ambient root inside a disposable guest while an external broker attenuates outward and durable effects. That differs from KeyKOS/EROS object-capability design, which removes ambient authority inside the system rather than granting root and constraining only its external consequences.

Ingress and egress are also not alternatives. Adversarial ingest can steer a decision; egress and durable mutation determine its consequences. The useful analysis follows:

```text
untrusted input -> decision -> capability use -> external/durable effect
```

C3 makes durable state an authority boundary. Whole-image persistence can preserve authority itself, so persisted authority needs expiry, revocation, and revalidation semantics; authority use and state mutation need separate provenance. Semantic competence and system authority should remain orthogonal: a stronger model is not entitled to more filesystem or network power merely because it occupies a higher inference tier.

The open research question is both semantic and ergonomic: can guest-local freedom plus attenuated effect capabilities resist confused-deputy and allowed-capability misuse while preserving the low-friction “open image” programming model?

## 9. The human is not one tier

Putting “human” at L3 collapses four roles:

1. **Oracle/exception handler:** answers a discrete miss.
2. **Supervisor:** receives state feedback and intervenes or reprograms intermittently.
3. **Practitioner:** performs enough work to retain skill and a situated process model.
4. **Governor/accountable authority:** authors policy and owns consequences.

The tier hierarchy directly represents only the first.

Sheridan and Verplank’s supervisory control already describes lower loops operating autonomously for restricted periods while a human monitors and intermittently acts or reprograms. [Sheridan and Verplank](https://ntrs.nasa.gov/api/citations/19790007441/downloads/19790007441.pdf) Parasuraman, Sheridan, and Wickens distinguish and model automation at information acquisition, analysis, decision selection, and action implementation. Their taxonomy supports stage-specific measurement; it does not itself prove how tiered inference transforms work. [Parasuraman et al.](https://doi.org/10.1109/3468.844354)

An ambient channel is therefore not a speculative contradiction to tiering. It belongs to supervisory control and can cross every tier:

```text
human observation / intervention / policy editing
------------------------------------------------->
 L0             L1                L2             escalations
```

### 9.1 Visibility has strong design ancestors, limited causal evidence here

Ecological interface design makes work-domain constraints perceptually available to support skill-, rule-, and knowledge-based control. [Vicente and Rasmussen](https://doi.org/10.1109/21.156574) Direct manipulation emphasizes continuous representations, rapid incremental reversible actions, and immediately visible effects. [Shneiderman](https://www.cs.umd.edu/~ben/papers/Shneiderman1983Direct.pdf) Calm technology treats center/periphery movement of information as an interface resource. [Weiser and Brown](https://calmtech.com/papers/designing-calm-technology)

VisiCalc is a concrete successful image-like system: expressions, values, and comments share visible state; dependencies recalculate; users apply domain knowledge through direct “what if” changes. [Frankston](https://rmf.vc/public/Essays/VisiCalcPaper.pdf) This supports visible state as a serious interface hypothesis. It does not prove that visibility lowers error or escalation rates.

Escalation volume is a poor sole outcome: a good view may increase warranted interventions. Measure state comprehension, prediction of the next state, detection time, intervention quality, false interventions, attention cost, unassisted recovery, and retention.

### 9.2 Deskilling is real but not a universal law of promotion

Bainbridge describes physical-skill decay through nonuse, loss of long-term operational knowledge without feedback, poor rare-event monitoring, and the difficulty of leaving humans only abnormal cases. [Bainbridge](https://gwern.net/doc/sociology/technology/1983-bainbridge.pdf) Endsley and Kiris experimentally found lower situation awareness and slower decisions after failure in one automated navigation task; operator control moderated the effect. [Endsley and Kiris](https://doi.org/10.1518/001872095779064555)

Kluge and Frank’s simulated-process studies distinguish knowledge from skill maintenance: active practice supported retained skill; symbolic rehearsal maintained knowledge but allowed moderate skill decay. [Kluge and Frank](https://doi.org/10.1080/00140139.2013.869357)

AI-specific evidence is mixed:

- A dynamic decision-game study with 189 participants found immediate assistance gains without measured degradation or carryover. [Karny et al.](https://par.nsf.gov/biblio/10553921-learning-ai-assistance-path-better-task-performance-dependence)
- A randomized programming-library study found worse conceptual understanding, code reading, and debugging on average. Within the AI-assisted condition, three cognitively engaged interaction patterns were associated with preserved outcomes; those patterns were not independently randomized. [Shen and Tamkin](https://arxiv.org/abs/2601.20245)
- Two preprint RCTs totaling 1,222 participants found lower immediate unassisted arithmetic/reading performance and persistence after short AI-assisted exposure; this is not evidence of long-term expert decay. [Liu et al.](https://arxiv.org/abs/2604.04721)

What is established: nonuse can degrade relevant skill; automation can cause out-of-loop state-awareness problems; knowledge and procedural skill can respond differently to maintenance interventions.

What remains open: whether promoting judgment down an inference hierarchy degrades residual expert competence, on what timescale, and what active practice schedule prevents it. Passive monitoring must not be assumed equivalent to active decision practice. A short experiment can test instrument reliability or immediate sensitivity; it cannot establish retained competence.

### 9.3 Where the remainder currently sits

The evidence does not select one of the brief’s three metaphysical positions.

- **Contingent:** models evaluated in the architecture-rationale study showed weak and inconsistent argument recovery, while domain specialists can fail under shift. This remains plausible and testable with current systems.
- **Structural:** external persistence removes one limitation, but continuous state integration, feedback, practice, and unassisted recovery remain incompletely supplied. The infrastructure directly probes this version.
- **Constitutive:** that meaning requires a subject for whom things matter is not settled by behavioral performance or model self-report.

The measurable remainder currently sits in **situated integration, feedback, supervisory competence, practice, and unassisted recovery**, not in a proved impossibility of machine theory-building. Accountable governance is a separate normative allocation of authority and consequence, not a measured capability deficit. The research can push the structural boundary. It cannot infer the constitutive conclusion from success or failure on E9.

## 10. History supplies constraints and bridge cases, not verdicts

Gabriel’s “Worse Is Better” essays are caricature, rebuttal, and counter-rebuttal, not a controlled causal account of why Lisp machines lost. [Essay history](https://www.dreamsongs.com/WorseIsBetter.html) His memoir identifies multiple pressures: proprietary hardware, standard-platform demand, memory footprint, mixed-language seams, AI overpromising, customer isolation, portability, and business decisions. [*Patterns of Software*](https://dreamsongs.com/Files/PatternsOfSoftware.pdf)

A useful Gabriel-derived design/economic hypothesis remains: mechanisms that require adoption of the whole integrated world face more resistance than mechanisms with portable standalone value. The history does not establish this as a universal law.

Emacs is a bridge case. It retained edit-the-running-program behavior through a Lisp extension layer atop portable C/Unix, with hot paths in C and user-defined functionality in Lisp. [Stallman](https://www.gnu.org/gnu/rms-lisp.html.en) It shows that live-system properties can be extracted into commodity infrastructure.

The spreadsheet is another bridge, not proof of a causal story. It combines visible durable state, direct manipulation, live recalculation, and user domain knowledge through a narrower visible grid and a different, often shallower modular abstraction model than general-purpose image environments. Its success motivates experiments on visible policy and state; it does not establish that visibility caused the Lisp machine/spreadsheet divergence.

The historical question is relational:

> Which coherent semantics require a shared runtime, which survive as a protocol or library on commodity substrates, and what do the seams cost?

## 11. Language is a two-axis experiment

Formal properties and model fluency are independent variables that can interact.

Low-resource programming-language and DSL work reports weaker direct generation, syntax sensitivity, negative transfer, and benefits from constrained decoding, continued pretraining, tokenizer adaptation, or execution-based reinforcement. [Low-resource/DSL survey](https://arxiv.org/abs/2410.03981), [CangjieBench](https://arxiv.org/abs/2603.14501), [No-resource languages](https://arxiv.org/abs/2606.16827), [Agnostics](https://openreview.net/forum?id=mjDT60Ffms), [Tokenizer adaptation](https://openreview.net/forum?id=CivRQcb6Wc)

This supports both halves of §7.1:

- training distribution affects model interaction with a substrate;
- the distribution is movable through data, tokenization, constraints, and feedback.

It does not provide an exchange rate between annotation budget and control semantics for this task.

### Research-substrate recommendation

**Recommendation:** use several substrates as controlled probes; do not choose a singular production language before the relations are measured. **Confidence: 0.9.**

| Substrate | Question it isolates |
|---|---|
| **Python** | Distribution/ecosystem baseline and explicit-protocol ergonomics |
| **Common Lisp** | Native named recovery and debugger-as-handler semantics |
| **Smalltalk/Dylan** | Minimal resumable exceptions and documented recovery protocols |
| **OCaml 5** | Typed-payload, one-shot delimited-control comparison |
| **Koka/Racket** | Multi-shot ceiling; Racket’s restricted transformed serialization |
| **Lean/F*/Dafny** | Admission/proof burden and semantic coverage |
| **Rust** | Ownership/typestate and a hardened authority/state membrane—not domain authorization |
| **Bend/HVM** | Frontier graph-sharing experiment, not load-bearing substrate |

The better language question is:

> Which semantic layer must the model see, and which can remain behind a typed protocol?

If the model emits only `restart_id + typed arguments + evidence`, host-language distribution matters less than when it authors free-form host code or proofs. It does not become irrelevant: language familiarity can still affect trace interpretation, tool use, semantic understanding, and selection.

The model-facing syntax and host runtime need not be the same language. A polyglot result is scientifically useful only if the seam is measured.

### 11.1 HVM/Bend: a narrower frontier question

Lafont’s interaction combinators establish a universal distributed graph-rewrite model with strong confluence under their rule constraints. [Lafont](https://doi.org/10.1006/inco.1997.2643) No cited proof establishes that every practical HVM2/HVM4 extension preserves those conditions. Where strong confluence holds, independent reduction orders for the same pure net are joinable. It does not give:

- termination;
- a choice among semantically different recoveries;
- safe duplication of external effects;
- cancellation or rollback of losing branches;
- persistent snapshots or version-compatible replay.

HVM’s superposition and duplication may still share downstream work among pure alternatives. The legitimate experiment is to normalize each backend against its own independent-replay baseline, then compare sharing ratio, memory amplification, wall time, and result multiset. “Speculative restarts for free” is an unsupported bridge.

Bend currently documents HVM2 targeting, continuations, GPU execution, weak single-core performance, early code generation, and NVIDIA-only acceleration. [Bend](https://github.com/HigherOrderCO/Bend) HVM4 describes itself as pre-launch. [HVM4](https://github.com/HigherOrderCO/hvm4) No inspected source established runtime graph checkpoint/migration or an external-effect protocol. Kind is public but minimally documented and its listed releases are stale; Bend2 and NeoGen lacked public inspectable implementations or independent benchmarks at the cutoff. [Kind](https://github.com/HigherOrderCO/Kind)

This makes HVM a useful ceiling probe, not a conclusion about the wider language question.

## 12. What is already built

This inventory says what can be reused and which relation it instantiates. It does not imply that the whole frame exists or that any component transfers unchanged.

| Reusable component | Examples | Relation supplied | Missing relation |
|---|---|---|---|
| Selective-risk methods | Chow, [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a.html) | accept/abstain objective | Stateful transitions, changing experts |
| Multi-expert deferral | Learning to Defer, multi-expert extensions | solver competence and deferral | Longitudinal promotion and human practice |
| LLM routers/cascades | FrugalGPT, RouteLLM, unified router/cascade, LLMRouterBench | cost/quality selection baselines | Stable production acceptance and drift |
| Semantic caches | GPTCache, vCache, SCALM, Krites | instance reuse and cache admission | Stateful action equivalence |
| Domain specialists | finance classifiers, laboratory-scale models, rationale-distilled students | bounded small-over-large results | Unified expert-tag mechanism and economics |
| Code-owned semantic execution | BINDER, LOTUS, lambda-RLM | code calls models as operators | Parked-frame recovery and bidirectional control |
| Model-owned external-state harnesses | RLM, RAH | model acts over external context/state | Need for fine-grained resumption |
| Named recovery runtimes | Common Lisp, Dylan | dynamically advertised recovery vocabulary and policy separation | Typed model selector and durability |
| Resumable exceptions | Smalltalk | resume/retry control actions | Application-defined reflective restart menu and durability |
| Effect/continuation runtimes | OCaml, Koka, Racket | delimited one-/multi-shot control | Reflective restart protocol and effect-safe forking |
| Durable engines | Temporal, Restate, DBOS, Inngest, Azure, Conductor | journal, replay, model/HITL pause | Arbitrary live-frame semantics |
| Formal admission | contracts, refinements, PCC, proof-carrying plans, Agent-C | checked propositions/policies | Adequate domain specs and tier-demotion evidence |
| Executable skills | Voyager, SkillsBench, SkillFoundry, SkillLearnBench, SkillEvolver | procedural accretion, reuse, and frontier continual learning | Reliable autonomous lifecycle across drift |
| Rule extraction/synthesis | TREPAN, VIPER, inductive synthesis, RuleChef | learned-to-symbolic representation change | Choosing scope and preserving rationale |
| Persistent object systems | KeyKOS, EROS | checkpoint, capabilities, resumption | Reproducible rebuild and rationale |
| Reproducible construction | Nix | declared static reconstruction | Mutable state/history/theory |
| Guest containment | Firecracker, gVisor | host isolation from untrusted guest execution | Effect-level least authority and allowed-channel misuse |
| Authority attenuation | KeyKOS/EROS, Capsicum, WASI | possession/descriptor/interface-scoped rights | Rootful-guest hybrid semantics and ergonomics |
| Supervisory interfaces | supervisory control, EID, direct manipulation, spreadsheets | continuous visibility and intervention vocabulary | Evaluation in tiered inference |
| Design-rationale systems | QOC, gIBIS, ADR traditions | explicit why/options/tradeoffs | Low-friction capture and promotion linkage |

The integrated conjunction not found in the reviewed sources is:

> a longitudinal system in which observed judgment structure drives solver selection and representation change; recovery choices have live and durable semantics; transitions are admitted against explicit constraints; provenance and rationale survive; and human supervision and practice are measured.

That sentence is a research hypothesis, not a product specification.

## 13. Bridges that do not currently follow

This is the kill list the evidence supports: invalid inferences and experiments that cannot answer their questions. It is not a list of already-existing mechanisms.

1. **“A flat ambiguity histogram kills tiering.”** It tests incidence concentration, not competence predictability, reusable equivalence, or compilation.
2. **“Repeated resolution permits promotion.”** Count is economic evidence only. Safe cache reuse, distillation, and rule extraction need different admission evidence.
3. **“Effects are the Common Lisp condition system formalized.”** Effects provide typed operations and continuations; named reflective recovery protocols are separate.
4. **“Python generators are general resumable conditions.”** They encode an explicit cooperative protocol but do not capture arbitrary callers, clone, or persist frames.
5. **“Durable execution serializes live frames.”** Mainstream engines replay declared histories; transformed serializable continuations are a different mechanism with restrictions.
6. **“Lafont-style confluence automatically holds for concrete HVM extensions and selects or validates speculative restarts.”** Preservation in HVM must first be established; reduction-order confluence still would not select among different semantic inputs or control effects.
7. **“Typechecking generated code proves the state transition admissible.”** Only a type encoding the relevant pre/postcondition can do that, relative to the model.
8. **“Root in a box removes the need for internal authority structure.”** Guest root and host-enforced capabilities solve different authority scopes.
9. **“A snapshot preserves theory.”** It preserves state. Provenance, rationale, schema meaning, and adaptive understanding are distinct.
10. **“Human at L3 represents presence.”** It represents availability on a miss. Supervision, practice, and governance cross the hierarchy.
11. **“Promotion necessarily deskills.”** Human-factors evidence establishes a risk mechanism, not a universal outcome for this workload.
12. **“E9 can test theory after the original team and rationale are gone.”** Without hidden ground truth it cannot distinguish reconstruction from plausible invention.
13. **“The spreadsheet won because state was visible” or “Lisp machines lost because coherence loses.”** Both are generative historical hypotheses, not established causal accounts.
14. **“Formal substrate quality and training distribution reduce to one language ranking.”** They are different axes; their interaction must be measured.

## 14. Revised research ladder

These are proposed studies, not approved loops. Each isolates a relation and leaves a reusable instrument. A negative result retires only the tested edge for the declared workload and evidence regime.

| Study | Smallest question | Action and comparison | Tool left behind | Interpretation boundary |
|---|---|---|---|---|
| **R0 — Locality atlas** | What cross-predictability, overlap, and transfer value exist among recurrence, resolution equivalence, solver competence, specialist generalization, and rule scope? | Build a chronological corpus of real judgment events. Record each primitive property separately; estimate pairwise mappings, strict subsets, conflicts, and future-split stability. | Ambiguity/locality profiler plus annotated corpus schema | Weak recurrence rejects cache reuse, not routing; weak four-way overlap does not reject useful pairwise mappings |
| **R1 — Selection baseline** | How do tier policies change the future risk–cost–coverage surface? | Compare best single expert, input-independent mixture/convex hull, cache, pre-router, two-tier cascade, longer chain, batch policy, and hindsight oracle. Include verification, rejected calls, training, labels, human attention, and error loss. | Longitudinal routing and acceptance-cost evaluator | Report Pareto surfaces and uncertainty. Dominance at one cost or coverage point does not erase behavior elsewhere |
| **R2 — Dependency audit** | Which ambiguities require immediate resolution to determine later work? | Classify control dependence and implement collect–resolve–rerun first. Replay matched cases. | Dependency schema and batch baseline | A batchable workload does not refute resumable control in domains with sequential dependence |
| **R3 — Recovery semantics matrix** | What comes from constrained recovery vocabulary, and what comes from each control operator? | Hold tasks and restart menu fixed. Compare free-form recovery; typed menu + pure/idempotent or journaled rerun; transfer to a named restart clause; one-shot resume at the signal/effect expression; and multi-shot branching. Score state/resource behavior separately. | Recovery corpus, language-neutral descriptor, and semantic conformance suite | Menu versus free form tests constrained choice. Rerun, restart transfer, one-shot resume, and multi-shot branch are separate hypotheses |
| **R4 — Live/durable correspondence** | Which recovery semantics can be represented faithfully by durable replay? | Fix the target semantics. Use Common Lisp for named restart transfer, OCaml/Racket/Koka for continuation resumption, and one durable engine for matched explicit replay. Inject crashes around request/journal/side-effect boundaries and code-version changes. | Durable-condition adapters and deterministic failure-injection suite | Reveals where context must be reified and where transfer/resume/replay cease to correspond; it need not select one universal mechanism |
| **R5 — Representation-change comparison** | Which recurring structures support cache, skill, specialist, or rule representation, and with what tradeoffs? | On the same R0 corpus, compare response reuse, targeted distillation, one-shot and iterative skills, and rule synthesis on frozen future data and drift slices. Use path-specific admission, provenance, shadowing, rollback, and retirement. | Promotion ledger and representation-specific evaluation adapters | Report cost–risk–coverage–interpretability–reversibility surfaces and boundary conditions; a dominated point can still reveal a transfer failure |
| **R6 — Admission factorial** | Which gain comes from specification expressiveness, which from checking machinery, and which from evidence/attestation? | Cross policy coverage (schema, executable/temporal predicate, refinement/postcondition) with checker (ordinary validator, SMT, proof checker) where representations permit. Evaluate formal certificates and PCAA-style evidence envelopes as different artifacts. Seed structural/semantic mutants and valid transitions; count specification production, trusted base, false rejects, and latency. | Versioned policy corpus, mutant/valid corpus, gate adapters, and coverage-burden report | No linear “proof ladder” follows unless policy coverage is held constant. Preserve the full Pareto surface |
| **R7 — Surface × semantics × data** | What is the exchange rate between model-facing distribution and backend control semantics? | Factor model-facing syntax (Python/Lisp/OCaml/Racket-shaped) against backend semantics (ordinary rerun, CL restart transfer, one-shot effect resume, multi-shot continuation), then vary constrained decoding and fixed data/fine-tuning budgets. | Cross-language semantic conformance suite and token/data/correctness profiler | Separates syntax fluency, runtime semantics, and seam effects; no global language winner is required |
| **R8a — Rationale reconstruction** | Can an evaluator recover why an existing form was chosen? | Give the post-decision artifact while hiding ADR/PR/interview rationale. Ask model and newcomer-human controls for constraints, alternatives, and reasons. Score historical concordance separately from the validity of different coherent explanations using blinded original-developer/domain-expert review. | Rationale-reconstruction corpus and blinded rubric | Low receipt overlap is not automatically failed theory if independently valid reasoning differs |
| **R8b — Prospective adaptation** | Can an evaluator recognize relevant similarity and adapt under a novel perturbation? | Give a pre-decision snapshot plus unseen change. Score proposed modifications with executable tests/invariants and blinded expert judgment, independently of R8a. | Counterfactual-change set and adaptation rubric | Tests adaptive use of an inferred theory, not historical reconstruction or constitutive meaning |
| **R9a — Human-instrument reliability** | Are the proposed visibility/practice measures repeatable and sensitive to immediate state differences? | Measure inter-rater and test–retest reliability plus immediate sensitivity for comprehension, prediction, catch, takeover, false intervention, attention, and unassisted recovery. | Visible-state surface and practice sampler | This validates measurement behavior only; retention requires repeated measures after nonuse |
| **R9b — Practice-constrained promotion** | How do promotion and human channel jointly affect competence over a declared retention interval? | Record baseline competence; randomize matched participants/tasks to no-promotion/manual-practice, paged oracle, passive ambient view, and active diagnosis/rehearsal; match exposure and measure assisted plus repeated unassisted performance. | Competence-aware promotion policy and longitudinal protocol | The manual-practice control is required to attribute decay or preservation; escalation count alone is not decisive |
| **R10 — Authority/image stages** | Can local freedom coexist with least-authority effects and reconstructible mutation? | Stage four tests: containment escape/resource abuse; authority attenuation/revocation; transition admission; reconstruction/recovery. Keep broker and credentials outside a rootful guest with deny-by-default networking, then test the conjunction. Include allowed-endpoint exfiltration/confused deputy, pre-revocation snapshot restore, duplicate external effects after restore, and compensation for irreversible effects. Treat rationale only as audit metadata. | Effect-boundary adversarial suite and image/provenance manifest | Each stage has its own evidence. A conjunction result must not substitute VM isolation for authority, admission, or recovery |
| **R11 — HVM sharing spike** | Does a concrete HVM runtime share pure speculative work better than its own replay baseline? | Compare each backend with its own independent-replay baseline. Report normalized sharing ratio, memory amplification, result multiset, and wall time; define HVM labels/correlations. Add handled algebraic state, then separately test non-rollbackable I/O. | Normalized multi-shot/share benchmark | Avoids comparing raw HVM interactions with Racket/Koka reductions; first establish whether the concrete runtime preserves required semantics |

The “hours, not weeks” preference must be budgeted per study rather than asserted globally. R0’s longitudinal corpus, R4’s multi-runtime fault matrix, R5’s four representation paths, and R7’s data sweep may require more than hours even at minimum credible scope. R9b must be longitudinal or explicitly limited to instrument behavior; shortening it would make the evidence incapable of answering retention.

### Comparable records, not one universal protocol

The recovery/durability comparison needs a narrow, versioned descriptor. A live Common Lisp restart object has dynamic extent; the record below is a stable reification of a recovery contract, not the object itself:

```text
Condition {
  occurrence_id, workflow_id, step_id,
  state_snapshot_handle, condition_type, payload,
  available_restart_descriptor_ids[]
}

RestartDescriptor {
  restart_id, contract_version, scope, lifetime,
  argument_schema, precondition, postcondition,
  transition_implementation_id, transition_version
}

Attempt {
  operation_id, attempt_id,
  provider_idempotency_key, provider_request_id?
}

Resolution {
  occurrence_id, restart_id, arguments,
  evidence_provenance, admission_receipt, outcome_receipt
}
```

Persist and pass a provider-recognized idempotency key **before** the external call; a provider request ID may become known only afterward. Persist workflow state/history separately. A hash alone cannot supply the current facts required to check a precondition, so the condition carries a versioned state snapshot or handle.

Other studies need linked records rather than more fields in the recovery protocol:

- **Selection:** solver/tier/version, prompt/tool versions, routing policy/version/score, candidate outputs, cost, and latency.
- **Admission:** checker and policy versions, evidence inputs, verdict, independent correctness evidence, and later outcome.
- **Promotion:** source events, target representation/version, scope, training or synthesis recipe, evaluation slices, provenance, rationale, rollback, and retirement state.

These records are measurement instruments. They do not imply one runtime architecture.

## 15. Tool inventory after this research

No code was created because no question or loop has been approved. The reusable output is this source map and the experimental decomposition above.

Existing tools and corpora that can prevent unnecessary rebuilding include:

- LLMRouterBench, RouteLLM, and FrugalGPT for solver-selection baselines;
- GPTCache/vCache and Krites for response-reuse mechanisms;
- LOTUS/BINDER/lambda-RLM for code-owned semantic operators;
- CodeAct, RLM/RAH, `dspy.RLM`, and Prime Intellect `verifiers` for model-owned code/state and harness-evaluation baselines; [DSPy RLM](https://github.com/stanfordnlp/dspy/blob/main/docs/docs/learn/programming/modules.md), [verifiers](https://docs.primeintellect.ai/verifiers/overview)
- native Common Lisp, OCaml, Koka, and Racket semantics for recovery comparisons;
- Temporal/Restate/DBOS/Inngest/Azure for durable replay rather than a new workflow engine;
- Lean/F*/Dafny and SMT solvers for the admission comparison;
- SkillsBench, Voyager, SkillFoundry, SkillLearnBench, SkillEvolver, TREPAN, VIPER, and RuleChef for representation-change baselines;
- KeyKOS/EROS, Firecracker/gVisor, Capsicum/WASI, and Nix as separate continuity/authority references.

The first new reusable capabilities should be:

1. the **locality-relationship profiler** from R0;
2. the **acceptance-cost and selection evaluator** from R1;
3. the **condition/restart conformance protocol** from R3;
4. the **promotion ledger** from R5;
5. the **visible-state and practice instrument** from R9a.

Each survives if the overall hierarchy fails.

## 16. Single sharpest open question

> **In a real longitudinal workload, what stable cross-predictability and transfer value connect reusable-resolution classes, cheapest-competent-solver regions, learnable-specialist domains, and deterministic-rule scopes under drift?**

Strong pairwise or partial mappings would be enough to make the computation-hierarchy frame compound: evidence collected for one mechanism could lower the cost of proposing or evaluating another without being mistaken for its admission proof.

Weak mappings would mean routing, semantic caching, specialist training, and rule extraction need largely independent controllers and evidence. They could still coexist in a hierarchy; the history would not unify their promotion logic.

That is the most informative next week of research because it tests the relation at the center without requiring the rest of the architecture to be true.

## Evidence boundary

This report maps source claims; it does not reproduce their benchmarks. Many 2026 results are preprints, project artifacts, or bounded issuer-reported evaluations. Historical essays and design papers supply concepts and hypotheses, not causal proof. “No integrated result found” means none was found in the reviewed primary sources, not that none exists.

Absence of a connection is deliberately not treated as evidence against the component. The open edges are the research.
