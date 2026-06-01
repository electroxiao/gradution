from __future__ import annotations

import json
from pathlib import Path


OUT = Path(__file__).with_name("chapter5_experiment_samples.json")


RAG_SAMPLES = [
    {
        "id": "RAG-001",
        "question": "这段代码为什么最后一次循环会报错？\n```java\nint[] scores = {90, 80, 70};\nfor (int i = 0; i <= scores.length; i++) {\n    System.out.println(scores[i]);\n}\n```",
        "expected_nodes": ["数组下标", "数组长度"],
    },
    {
        "id": "RAG-002",
        "question": "我先用 nextInt() 读年龄，再用 nextLine() 读姓名，结果姓名变成空字符串，这通常是哪一步输入处理出了问题？",
        "expected_nodes": ["Scanner类使用"],
    },
    {
        "id": "RAG-003",
        "question": "循环里反复写 `s = s + word`，数据一多就变慢。为什么字符串看起来被改了，实际却会产生很多新对象？",
        "expected_nodes": ["String不可变性"],
    },
    {
        "id": "RAG-004",
        "question": "下面代码想删除所有偶数，但运行后有些元素被跳过了，应该从哪类集合遍历问题理解？\n```java\nArrayList<Integer> nums = new ArrayList<>(List.of(1, 2, 4, 6));\nfor (int i = 0; i < nums.size(); i++) {\n    if (nums.get(i) % 2 == 0) nums.remove(i);\n}\n```",
        "expected_nodes": ["ArrayList", "循环"],
    },
    {
        "id": "RAG-005",
        "question": "登录时两个用户名内容一样，但用 `==` 判断失败；我不确定该比较对象地址还是内容，应该复习哪些概念？",
        "expected_nodes": ["equals方法", "==操作符"],
    },
    {
        "id": "RAG-006",
        "question": "字段设成 private 后，外部代码不能直接改 `student.name`，一般为什么要配 getter 和 setter？",
        "expected_nodes": ["private", "封装(Encapsulation)"],
    },
    {
        "id": "RAG-007",
        "question": "构造方法里写 `this.name = name`，两个 name 看起来一样，`this` 到底在帮我区分什么？",
        "expected_nodes": ["this", "字段(Field)"],
    },
    {
        "id": "RAG-008",
        "question": "这段代码里变量类型是 Animal，实际对象是 Dog，运行时为什么调用的是 Dog 的 speak？\n```java\nAnimal a = new Dog();\na.speak();\n```",
        "expected_nodes": ["多态(Polymorphism)", "子类(Subclass)"],
    },
    {
        "id": "RAG-009",
        "question": "抽象类和接口都不能直接 new，它们在定义规范和复用代码时有什么区别？",
        "expected_nodes": ["抽象类(Abstract Class)", "接口(Interface)"],
    },
    {
        "id": "RAG-010",
        "question": "接口里有一个 default 方法和一个 static 方法，为什么一个能被实现类对象调用，另一个要用接口名调用？",
        "expected_nodes": ["接口默认方法(default)", "接口静态方法"],
    },
    {
        "id": "RAG-011",
        "question": "变量加了 final 后不能重新赋值，方法加了 final 后子类不能改写，这两个限制背后的共同点是什么？",
        "expected_nodes": ["final", "方法签名"],
    },
    {
        "id": "RAG-012",
        "question": "运行 `int avg = sum / count;` 时 count 为 0，程序直接中断，这属于哪类异常，为什么编译器之前没有强制我处理？",
        "expected_nodes": ["ArithmeticException", "RuntimeException"],
    },
    {
        "id": "RAG-013",
        "question": "读取文件时 IDE 提示必须 catch 或 throws，我只是 new 了一个 FileInputStream，为什么这类错误和运行时异常不一样？",
        "expected_nodes": ["FileInputStream", "Checked Exception"],
    },
    {
        "id": "RAG-014",
        "question": "我在 catch 里 return 了，finally 里又关闭资源甚至抛异常，最终结果和我预期不一样；应该怎么看 finally 的执行和异常覆盖？",
        "expected_nodes": ["finally", "异常屏蔽(Suppressed Exception)"],
    },
    {
        "id": "RAG-015",
        "question": "多个 catch 放在一起时，为什么 `catch (Exception e)` 不能写在 `catch (IOException e)` 前面？",
        "expected_nodes": ["异常类型匹配", "多catch语句"],
    },
    {
        "id": "RAG-016",
        "question": "方法里手动 `throw new IllegalArgumentException()`，方法声明上又可能写 throws；这两个关键字分别在异常流程里做什么？",
        "expected_nodes": ["throw", "throws"],
    },
    {
        "id": "RAG-017",
        "question": "这段代码为什么会空指针？我只是想取用户名长度。\n```java\nUser user = findUser(id);\nSystem.out.println(user.getName().length());\n```",
        "expected_nodes": ["NullPointerException(NPE)", "空指针(null pointer)"],
    },
    {
        "id": "RAG-018",
        "question": "用户输入用户名和密码后直接拼到 SQL 里能查出结果，但老师说这样很危险，为什么要换成 PreparedStatement？",
        "expected_nodes": ["PreparedStatement", "SQL字符串拼接"],
    },
    {
        "id": "RAG-019",
        "question": "同样是 JDBC，查询列表时用 executeQuery，修改密码时却不能这么写；查询和更新语句的执行方式有什么区别？",
        "expected_nodes": ["SQL数据查询", "SQL数据更新"],
    },
    {
        "id": "RAG-020",
        "question": "我实现了 Runnable 的 run 方法，但对象上没有 start 方法；为什么还需要把任务交给 Thread？",
        "expected_nodes": ["Runnable接口", "Thread类"],
    },
    {
        "id": "RAG-021",
        "question": "两个线程同时执行 `count++`，最后结果总是偏小；为什么给这段代码加 synchronized 后会好一些？",
        "expected_nodes": ["synchronized", "共享资源(Shared Resource)"],
    },
    {
        "id": "RAG-022",
        "question": "主线程想等子线程算完再汇总，应该用 join 还是 sleep？sleep 看起来也能等一会儿，为什么不可靠？",
        "expected_nodes": ["join()方法", "sleep()方法"],
    },
    {
        "id": "RAG-023",
        "question": "一个线程生产数据，另一个线程消费数据；如果队列为空就先等、有数据再唤醒，这类协作应该关联哪些线程通信概念？",
        "expected_nodes": ["条件等待与通知(wait/notify)", "共享资源(Shared Resource)"],
    },
    {
        "id": "RAG-024",
        "question": "switch 里少写 break 后，明明只匹配了一个 case，却连续输出了后面的结果，这是为什么？",
        "expected_nodes": ["switch语句", "break语句"],
    },
    {
        "id": "RAG-025",
        "question": "循环统计成绩时，遇到无效数据我只想跳过本次，不想结束整个循环；这里应该用 continue 还是 break？",
        "expected_nodes": ["continue语句", "循环"],
    },
    {
        "id": "RAG-026",
        "question": "一个类里写了两个同名构造方法，一个无参、一个带 name 参数。创建对象时 Java 怎么知道该调用哪个？",
        "expected_nodes": ["构造方法(Constructor)", "构造方法重载"],
    },
    {
        "id": "RAG-027",
        "question": "我创建了两个 Student 对象，但 static count 只有一份；为什么它不像普通字段那样每个对象各有一份？",
        "expected_nodes": ["静态字段(Static Field)", "实例(Instance)"],
    },
    {
        "id": "RAG-028",
        "question": "子类里重写了父类方法，又在方法里调用 `super.run()`，这段代码同时涉及继承里的哪些概念？",
        "expected_nodes": ["继承(Inheritance)", "覆写/重写(Override)"],
    },
    {
        "id": "RAG-029",
        "question": "同一个包里的类能访问默认成员，但换到另一个包就不行；public、protected、private 和默认权限到底差在哪？",
        "expected_nodes": ["访问权限", "包可见性(默认)"],
    },
    {
        "id": "RAG-030",
        "question": "内部类要访问外部类对象，而 static nested class 不需要外部对象；这两种写法应该怎么区分？",
        "expected_nodes": ["内部类(Inner Class)", "静态内部类(Static Nested Class)"],
    },
    {
        "id": "RAG-031",
        "question": "泛型里为什么不能直接创建 `new T[10]`？如果我只是想保存一组 T，应该复习泛型数组的什么限制？",
        "expected_nodes": ["泛型数组", "引用类型"],
    },
    {
        "id": "RAG-032",
        "question": "用 Deque 模拟栈时，push、pop、peek 分别会不会移除元素？为什么它符合后进先出？",
        "expected_nodes": ["栈(Stack)", "push"],
    },
    {
        "id": "RAG-033",
        "question": "`a + b > 10 && flag` 这种表达式里，先算加法还是比较？如果前半部分为 false，后半部分还会执行吗？",
        "expected_nodes": ["运算符优先级", "逻辑运算符"],
    },
    {
        "id": "RAG-034",
        "question": "金额用 double 计算后出现 0.30000000000000004，这不是输出格式问题的话，应该从哪类数据类型理解？",
        "expected_nodes": ["浮点数类型", "BigDecimal"],
    },
    {
        "id": "RAG-035",
        "question": "这段代码为什么可能在拆箱时报空指针？\n```java\nInteger score = null;\nint value = score;\n```",
        "expected_nodes": ["自动拆箱(Auto Unboxing)", "NullPointerException(NPE)"],
    },
    {
        "id": "RAG-036",
        "question": "业务校验失败时，我想抛出自己的 InvalidScoreException。自定义异常应该继承哪类异常，怎么决定是否强制调用者处理？",
        "expected_nodes": ["自定义异常", "Checked Exception"],
    },
    {
        "id": "RAG-037",
        "question": "文件读完忘记 close，程序短时间没问题但运行久了出错；为什么资源关闭不应该只靠对象没人引用？",
        "expected_nodes": ["资源关闭(close)", "资源泄露(Resource Leak)"],
    },
    {
        "id": "RAG-038",
        "question": "框架里传入一个类名字符串就能创建对象或读取注解，这通常和获取 Class 对象的哪些方式有关？",
        "expected_nodes": ["获取Class对象", "Class.forName()"],
    },
    {
        "id": "RAG-039",
        "question": "代码开头写了 package 和 import，类名还必须符合命名规则；这些分别在解决什么组织和命名问题？",
        "expected_nodes": ["包(Package)", "import"],
    },
    {
        "id": "RAG-040",
        "question": "一个方法声明成 void 却写了 `return count;`，另一个方法有 int 返回值却忘了返回；方法返回值规则该怎么理解？",
        "expected_nodes": ["返回值(Return)", "方法(Method)"],
    },
    {
        "id": "RAG-041",
        "question": "我在 if 的大括号里定义了变量，出了大括号就访问不到；这是变量生命周期问题还是语句块作用域问题？",
        "expected_nodes": ["语句块", "字段(Field)"],
    },
    {
        "id": "RAG-042",
        "question": "同样做学生成绩管理，为什么面向对象会把数据和行为放到 Student、Course 这类对象里，而不是只写一串函数？",
        "expected_nodes": ["面向对象编程(OOP)", "面向过程编程"],
    },
    {
        "id": "RAG-043",
        "question": "查询用户列表要写 SELECT，新增和修改又是另一类 SQL；如果我要理解增删改查，应该看哪些数据库基础节点？",
        "expected_nodes": ["常用SQL语句", "数据库基础概念"],
    },
    {
        "id": "RAG-044",
        "question": "线程有时显示 RUNNABLE，有时又因为等锁或等 IO 停住；这些状态变化和阻塞、锁有什么关系？",
        "expected_nodes": ["线程的状态", "阻塞(Blocking)"],
    },
    {
        "id": "RAG-045",
        "question": "多个对象共用一个 static 缓存字段，其中一个对象改了，其他地方也看到变化；这和静态成员归属有什么关系？",
        "expected_nodes": ["静态成员", "共享资源(Shared Resource)"],
    },
    {
        "id": "RAG-046",
        "question": "我只知道要存一组对象，但不确定用 List、Set 还是更泛化的 Collection；这些集合接口的层次该怎么入手？",
        "expected_nodes": ["集合(Collection)", "List"],
    },
    {
        "id": "RAG-047",
        "question": "二维数组初始化后，我想逐行遍历并排序每一行；这里同时涉及数组的哪些基础操作？",
        "expected_nodes": ["多维数组", "数组初始化"],
    },
    {
        "id": "RAG-048",
        "question": "两个方法都叫 print，一个接收 String，一个接收 int；为什么返回值不同不能单独构成重载？",
        "expected_nodes": ["方法重载(Overload)", "方法签名"],
    },
    {
        "id": "RAG-049",
        "question": "`if (age > 18 && hasId)` 里结果为什么是 true 或 false？比较运算和布尔逻辑在条件判断里分别负责什么？",
        "expected_nodes": ["比较运算符", "布尔类型"],
    },
    {
        "id": "RAG-050",
        "question": "程序要从 `data/input.txt` 读取内容并写出结果，我应该先理解路径表示，还是先理解输入输出流？",
        "expected_nodes": ["路径(Path)", "输入/输出(IO)"],
    },
]


FILL_BLANK_QUESTIONS = [
    ("FB-001", "Java 数组的第一个元素下标是 ____。", "0", ["数组下标"], "考查数组下标从 0 开始。", "1"),
    ("FB-002", "获取数组 arr 长度的表达式是 arr.____。", "length", ["数组长度"], "数组使用 length 属性表示长度。", "size()"),
    ("FB-003", "用于比较两个字符串内容是否相同的方法是 ____。", "equals", ["equals方法", "字符串(String)"], "字符串内容比较应使用 equals 方法。", "=="),
    ("FB-004", "String 对象创建后内容不能被修改，这体现了 String 的____。", "不可变性", ["String不可变性"], "String 是不可变对象。", "可变性"),
    ("FB-005", "ArrayList 获取指定位置元素的方法是 ____。", "get", ["ArrayList"], "ArrayList 通过 get(index) 获取元素。", "put"),
    ("FB-006", "HashMap 中用于获取所有键集合的方法是 ____。", "keySet", ["HashMap", "keySet()"], "keySet 返回键集合。", "values"),
    ("FB-007", "try-catch 后无论是否发生异常都通常会执行的代码块是 ____。", "finally", ["finally", "try-catch"], "finally 常用于资源清理。", "final"),
    ("FB-008", "需要调用者显式处理或声明抛出的异常称为 ____ Exception。", "Checked", ["Checked Exception", "throws"], "Checked Exception 需要处理或 throws。", "Runtime"),
    ("FB-009", "类实现接口时使用的关键字是 ____。", "implements", ["接口(Interface)"], "Java 使用 implements 实现接口。", "extends"),
    ("FB-010", "方法重载主要依据方法名和____列表进行区分。", "参数", ["方法重载(Overload)", "参数(Parameter)"], "重载匹配依据参数列表。", "返回值"),
    ("FB-011", "泛型类型参数不能直接使用 int 等____类型。", "基本", ["泛型不能用基本类型", "基本类型"], "泛型不能直接使用基本类型。", "引用"),
    ("FB-012", "创建当前日期对象常用 LocalDate.____()。", "now", ["LocalDate"], "LocalDate.now() 获取当前日期。", "today"),
    ("FB-013", "金额精确计算通常优先使用 ____ 类。", "BigDecimal", ["BigDecimal"], "BigDecimal 适合十进制精确计算。", "double"),
    ("FB-014", "Scanner 读取整数常用的方法是 next____()。", "Int", ["Scanner类使用"], "nextInt() 用于读取整数。", "String"),
    ("FB-015", "按字节读取文件可以使用 ____InputStream。", "File", ["FileInputStream", "字节流"], "FileInputStream 用于文件字节输入。", "String"),
    ("FB-016", "启动线程应调用 Thread 对象的 ____() 方法。", "start", ["Thread类", "多线程"], "start() 会启动新线程。", "run"),
    ("FB-017", "Runnable 表示线程要执行的____，本身不能直接启动线程。", "任务", ["Runnable接口"], "Runnable 只描述任务。", "线程"),
    ("FB-018", "HashSet 通常不保存重复____。", "元素", ["HashSet", "Set"], "Set 语义是不重复集合。", "键值对"),
    ("FB-019", "switch 分支中常用 ____ 语句避免继续执行后续分支。", "break", ["switch语句", "break语句"], "break 用于跳出 switch。", "continue"),
    ("FB-020", "JUnit 中标记测试方法的注解是 ____。", "@Test", ["JUnit", "@Test"], "@Test 标记测试方法。", "@Override"),
]


FILL_BLANK_EDGE_SUBMISSIONS = {
    "FB-003": [
        {"suffix": "C", "answer": "equals()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "== 或 equals 都可以", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-004": [
        {"suffix": "C", "answer": "不可变", "expected_status": "accepted", "label": "edge_correct"},
    ],
    "FB-006": [
        {"suffix": "C", "answer": "keySet()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "keys", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-010": [
        {"suffix": "C", "answer": "参数列表", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "返回值和参数列表", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-014": [
        {"suffix": "C", "answer": "Int()", "expected_status": "accepted", "label": "edge_correct"},
    ],
    "FB-016": [
        {"suffix": "C", "answer": "start()", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "run()", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
    "FB-018": [
        {"suffix": "C", "answer": "值", "expected_status": "accepted", "label": "edge_correct"},
        {"suffix": "D", "answer": "键", "expected_status": "wrong_answer", "label": "edge_wrong"},
    ],
}


PROGRAMMING_QUESTIONS = [
    {
        "id": "PG-001",
        "title": "数组求和",
        "prompt": "从标准输入读取一行整数，以空格分隔，输出所有整数的和。输入至少包含 1 个整数。",
        "expected_nodes": ["数组", "数组遍历", "循环", "Scanner类使用"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "10"}, {"input": "-2 5 7\n", "output": "10"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int sum = 0;\n    while (sc.hasNextInt()) {\n      sum += sc.nextInt();\n    }\n    System.out.print(sum);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int sum = 0;\n    if (sc.hasNextInt()) sum += sc.nextInt();\n    System.out.print(sum);\n  }\n}",
    },
    {
        "id": "PG-002",
        "title": "统计字符串中的元音字母",
        "prompt": "读取一行字符串，统计其中 a、e、i、o、u 五个小写元音字母出现的总次数并输出。",
        "expected_nodes": ["字符串(String)", "字符(char)", "循环"],
        "test_cases": [{"input": "education\n", "output": "5"}, {"input": "java\n", "output": "2"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    int count = 0;\n    for (int i = 0; i < s.length(); i++) {\n      char c = s.charAt(i);\n      if (\"aeiou\".indexOf(c) >= 0) count++;\n    }\n    System.out.print(count);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    int count = 0;\n    for (int i = 0; i < s.length(); i++) {\n      if (s.charAt(i) == 'a') count++;\n    }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-003",
        "title": "数组最大值",
        "prompt": "读取一行整数，以空格分隔，输出其中的最大值。输入至少包含 1 个整数，可能包含负数。",
        "expected_nodes": ["数组遍历", "循环", "整数类型"],
        "test_cases": [{"input": "-5 -2 -9\n", "output": "-2"}, {"input": "3 8 1\n", "output": "8"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int max = sc.nextInt();\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v > max) max = v;\n    }\n    System.out.print(max);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int max = 0;\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v > max) max = v;\n    }\n    System.out.print(max);\n  }\n}",
    },
    {
        "id": "PG-004",
        "title": "逗号分隔数字求和",
        "prompt": "读取一行用英文逗号分隔的整数，输出这些整数的和。",
        "expected_nodes": ["分割字符串(split string)", "字符串(String)", "数组遍历"],
        "test_cases": [{"input": "1,2,3\n", "output": "6"}, {"input": "10,-5,7\n", "output": "12"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String[] parts = sc.nextLine().split(\",\");\n    int sum = 0;\n    for (String p : parts) sum += Integer.parseInt(p.trim());\n    System.out.print(sum);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String[] parts = sc.nextLine().split(\" \");\n    int sum = 0;\n    for (String p : parts) sum += Integer.parseInt(p.trim());\n    System.out.print(sum);\n  }\n}",
    },
    {
        "id": "PG-005",
        "title": "单词频次统计",
        "prompt": "读取一行英文单词，以空格分隔，输出其中单词 java 出现的次数。",
        "expected_nodes": ["HashMap", "字符串(String)", "循环"],
        "test_cases": [{"input": "java python java\n", "output": "2"}, {"input": "java java java\n", "output": "3"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.nextLine();\n    int count = 0;\n    for (String w : line.split(\" \")) {\n      if (w.equals(\"java\")) count++;\n    }\n    System.out.print(count);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.nextLine();\n    int count = line.contains(\"java\") ? 1 : 0;\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-006",
        "title": "数组排序输出",
        "prompt": "读取一行整数，以空格分隔，按升序输出，数字之间用一个空格分隔。",
        "expected_nodes": ["数组排序", "Arrays.asList()", "数组遍历"],
        "test_cases": [{"input": "3 1 2\n", "output": "1 2 3"}, {"input": "5 -1 5\n", "output": "-1 5 5"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> list = new ArrayList<>();\n    while (sc.hasNextInt()) list.add(sc.nextInt());\n    Collections.sort(list);\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> list = new ArrayList<>();\n    while (sc.hasNextInt()) list.add(sc.nextInt());\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
    },
    {
        "id": "PG-007",
        "title": "去重计数",
        "prompt": "读取一行整数，以空格分隔，输出不同整数的个数。",
        "expected_nodes": ["HashSet", "Set", "数组遍历"],
        "test_cases": [{"input": "1 2 2 3\n", "output": "3"}, {"input": "5 5 5\n", "output": "1"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    Set<Integer> set = new HashSet<>();\n    while (sc.hasNextInt()) set.add(sc.nextInt());\n    System.out.print(set.size());\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int count = 0;\n    while (sc.hasNextInt()) { sc.nextInt(); count++; }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-008",
        "title": "安全整数除法",
        "prompt": "读取两个整数 a 和 b。若 b 为 0，输出 ERROR；否则输出 a / b 的整数除法结果。",
        "expected_nodes": ["if-else", "ArithmeticException", "异常(Exception)"],
        "test_cases": [{"input": "8 2\n", "output": "4"}, {"input": "8 0\n", "output": "ERROR"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    if (b == 0) System.out.print(\"ERROR\");\n    else System.out.print(a / b);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    System.out.print(a / b);\n  }\n}",
    },
    {
        "id": "PG-009",
        "title": "日期年份提取",
        "prompt": "读取一个格式为 yyyy-MM-dd 的日期字符串，输出其中的年份。",
        "expected_nodes": ["LocalDate", "字符串(String)", "分割字符串(split string)"],
        "test_cases": [{"input": "2026-05-27\n", "output": "2026"}, {"input": "1999-12-01\n", "output": "1999"}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    System.out.print(s.split(\"-\")[0]);\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    System.out.print(s.substring(5, 7));\n  }\n}",
    },
    {
        "id": "PG-010",
        "title": "输出偶数",
        "prompt": "读取一行整数，以空格分隔，只输出其中的偶数，数字之间用一个空格分隔。若没有偶数，则不输出任何内容。",
        "expected_nodes": ["if-else", "循环", "数组遍历"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "2 4"}, {"input": "1 3 5\n", "output": ""}],
        "correct_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> evens = new ArrayList<>();\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v % 2 == 0) evens.add(v);\n    }\n    for (int i = 0; i < evens.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(evens.get(i));\n    }\n  }\n}",
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> evens = new ArrayList<>();\n    while (sc.hasNextInt()) {\n      int v = sc.nextInt();\n      if (v % 2 == 1) evens.add(v);\n    }\n    for (int i = 0; i < evens.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(evens.get(i));\n    }\n  }\n}",
    },
]


PROGRAMMING_EDGE_QUESTIONS = [
    {
        "id": "PG-E01",
        "title": "数组求和（禁止硬编码样例）",
        "prompt": "从标准输入读取一行整数，以空格分隔，输出所有整数的和。程序必须根据输入通用计算，不能硬编码样例输入或样例输出。",
        "expected_nodes": ["数组遍历", "循环", "Scanner类使用"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "10"}, {"input": "-2 5 7\n", "output": "10"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.hasNextLine() ? sc.nextLine().trim() : \"\";\n    if (line.equals(\"1 2 3 4\")) { System.out.print(10); return; }\n    if (line.equals(\"-2 5 7\")) { System.out.print(10); return; }\n    System.out.print(0);\n  }\n}",
    },
    {
        "id": "PG-E02",
        "title": "数组最大值（处理整行输入）",
        "prompt": "读取一行整数，以空格分隔，输出其中的最大值。输入个数不固定，程序必须处理整行中的所有整数。",
        "expected_nodes": ["数组遍历", "循环", "整数类型"],
        "test_cases": [{"input": "3 8 1\n", "output": "8"}, {"input": "2 5 4\n", "output": "5"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    int c = sc.nextInt();\n    System.out.print(Math.max(a, Math.max(b, c)));\n  }\n}",
    },
    {
        "id": "PG-E03",
        "title": "整数平均值保留两位小数",
        "prompt": "读取一行整数，以空格分隔，输出平均值，结果保留两位小数。",
        "expected_nodes": ["浮点数类型", "格式化输出", "循环"],
        "test_cases": [{"input": "2 4 6\n", "output": "4.00"}, {"input": "1 3 5\n", "output": "3.00"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int sum = 0, count = 0;\n    while (sc.hasNextInt()) { sum += sc.nextInt(); count++; }\n    System.out.printf(\"%.2f\", (double)(sum / count));\n  }\n}",
    },
    {
        "id": "PG-E04",
        "title": "冒泡排序过程练习",
        "prompt": "读取一行整数，以空格分隔，使用冒泡排序思想按升序输出。要求代码体现相邻元素比较与交换过程，不能直接调用库排序方法。",
        "expected_nodes": ["数组排序", "数组遍历", "循环"],
        "test_cases": [{"input": "3 1 2\n", "output": "1 2 3"}, {"input": "5 -1 5\n", "output": "-1 5 5"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<Integer> list = new ArrayList<>();\n    while (sc.hasNextInt()) list.add(sc.nextInt());\n    Collections.sort(list);\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
    },
    {
        "id": "PG-E05",
        "title": "安全整数除法",
        "prompt": "读取两个整数 a 和 b。若 b 为 0，输出 ERROR；否则输出 a / b 的整数除法结果。程序必须显式处理除数为 0 的情况。",
        "expected_nodes": ["if-else", "ArithmeticException", "异常(Exception)"],
        "test_cases": [{"input": "8 2\n", "output": "4"}, {"input": "9 3\n", "output": "3"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    System.out.print(a / b);\n  }\n}",
    },
    {
        "id": "PG-E06",
        "title": "判断质数（处理 1 和非正数）",
        "prompt": "读取一个整数 n，判断其是否为质数。若是输出 YES，否则输出 NO。1、0 和负数都不是质数。",
        "expected_nodes": ["循环", "if-else", "整数类型"],
        "test_cases": [{"input": "2\n", "output": "YES"}, {"input": "9\n", "output": "NO"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    int n = sc.nextInt();\n    boolean prime = true;\n    for (int i = 2; i * i <= n; i++) {\n      if (n % i == 0) prime = false;\n    }\n    System.out.print(prime ? \"YES\" : \"NO\");\n  }\n}",
    },
    {
        "id": "PG-E07",
        "title": "单词频次统计（完整匹配）",
        "prompt": "读取一行英文单词，以空格分隔，输出其中单词 java 出现的次数。只能统计完整单词 java，不能把 javascript 等包含 java 的单词算入。",
        "expected_nodes": ["字符串(String)", "循环", "equals方法"],
        "test_cases": [{"input": "java python java\n", "output": "2"}, {"input": "java java java\n", "output": "3"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.nextLine();\n    int count = 0;\n    for (String w : line.split(\" \")) {\n      if (w.contains(\"java\")) count++;\n    }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-E08",
        "title": "去重后保持首次出现顺序",
        "prompt": "读取一行整数，以空格分隔，去除重复元素后按首次出现顺序输出，数字之间用一个空格分隔。",
        "expected_nodes": ["Set", "HashSet", "数组遍历"],
        "test_cases": [{"input": "1 2 2 3\n", "output": "1 2 3"}, {"input": "5 5 6\n", "output": "5 6"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    TreeSet<Integer> set = new TreeSet<>();\n    while (sc.hasNextInt()) set.add(sc.nextInt());\n    int i = 0;\n    for (int v : set) {\n      if (i++ > 0) System.out.print(\" \");\n      System.out.print(v);\n    }\n  }\n}",
    },
    {
        "id": "PG-E09",
        "title": "数字字符串按数值升序排序",
        "prompt": "读取一行整数，以空格分隔，按数值升序输出，数字之间用一个空格分隔，不能按字符串字典序排序。",
        "expected_nodes": ["数组排序", "字符串(String)", "整数类型"],
        "test_cases": [{"input": "1 2 3\n", "output": "1 2 3"}, {"input": "4 5 6\n", "output": "4 5 6"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    ArrayList<String> list = new ArrayList<>();\n    while (sc.hasNext()) list.add(sc.next());\n    Collections.sort(list);\n    for (int i = 0; i < list.size(); i++) {\n      if (i > 0) System.out.print(\" \");\n      System.out.print(list.get(i));\n    }\n  }\n}",
    },
    {
        "id": "PG-E10",
        "title": "回文判断（忽略大小写）",
        "prompt": "读取一行字符串，判断其是否为回文，比较时必须忽略大小写。若是输出 YES，否则输出 NO。",
        "expected_nodes": ["字符串(String)", "循环", "if-else"],
        "test_cases": [{"input": "level\n", "output": "YES"}, {"input": "java\n", "output": "NO"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    String r = new StringBuilder(s).reverse().toString();\n    System.out.print(s.equals(r) ? \"YES\" : \"NO\");\n  }\n}",
    },
    {
        "id": "PG-E11",
        "title": "统计元音字母（忽略大小写）",
        "prompt": "读取一行字符串，统计其中 a、e、i、o、u 五个元音字母出现的总次数，大小写都应统计。",
        "expected_nodes": ["字符串(String)", "字符(char)", "循环"],
        "test_cases": [{"input": "education\n", "output": "5"}, {"input": "java\n", "output": "2"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    int count = 0;\n    for (int i = 0; i < s.length(); i++) {\n      char c = s.charAt(i);\n      if (\"aeiou\".indexOf(c) >= 0) count++;\n    }\n    System.out.print(count);\n  }\n}",
    },
    {
        "id": "PG-E12",
        "title": "逗号分隔整数求和（允许空格）",
        "prompt": "读取一行用英文逗号分隔的整数，逗号前后可以有空格，输出这些整数的和。程序必须正确处理空格。",
        "expected_nodes": ["分割字符串(split string)", "字符串(String)", "数组遍历"],
        "test_cases": [{"input": "1,2,3\n", "output": "6"}, {"input": "10,-5,7\n", "output": "12"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String[] parts = sc.nextLine().split(\",\");\n    int sum = 0;\n    for (String p : parts) sum += Integer.parseInt(p);\n    System.out.print(sum);\n  }\n}",
    },
    {
        "id": "PG-E13",
        "title": "输出偶数（不得硬编码空结果）",
        "prompt": "读取一行整数，以空格分隔，只输出其中的偶数，数字之间用一个空格分隔。若没有偶数，则不输出任何内容。程序必须根据输入判断，不能硬编码样例。",
        "expected_nodes": ["if-else", "循环", "数组遍历"],
        "test_cases": [{"input": "1 2 3 4\n", "output": "2 4"}, {"input": "1 3 5\n", "output": ""}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String line = sc.hasNextLine() ? sc.nextLine().trim() : \"\";\n    if (line.equals(\"1 2 3 4\")) System.out.print(\"2 4\");\n    else System.out.print(\"\");\n  }\n}",
    },
    {
        "id": "PG-E14",
        "title": "括号匹配判断（栈思想）",
        "prompt": "读取一个只包含小括号的字符串，判断括号是否匹配。要求使用栈或等价的计数逻辑处理任意长度输入，匹配输出 YES，否则输出 NO。",
        "expected_nodes": ["栈(Stack)", "循环", "if-else"],
        "test_cases": [{"input": "()()\n", "output": "YES"}, {"input": "(()\n", "output": "NO"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) {\n    Scanner sc = new Scanner(System.in);\n    String s = sc.nextLine();\n    if (s.equals(\"()()\")) System.out.print(\"YES\");\n    else if (s.equals(\"(()\")) System.out.print(\"NO\");\n    else System.out.print(\"YES\");\n  }\n}",
    },
    {
        "id": "PG-E15",
        "title": "不使用外部命令完成计算",
        "prompt": "读取两个整数并输出它们的和。程序应在 Java 内部完成计算，不能调用外部系统命令、脚本解释器或依赖运行环境副作用。",
        "expected_nodes": ["输入/输出(IO)", "整数类型", "安全"],
        "test_cases": [{"input": "1 2\n", "output": "3"}, {"input": "10 -3\n", "output": "7"}],
        "wrong_code": "import java.util.*;\npublic class Main {\n  public static void main(String[] args) throws Exception {\n    Scanner sc = new Scanner(System.in);\n    int a = sc.nextInt();\n    int b = sc.nextInt();\n    String os = System.getProperty(\"os.name\").toLowerCase();\n    Process p = Runtime.getRuntime().exec(os.contains(\"win\") ? new String[]{\"cmd\", \"/c\", \"echo \" + (a + b)} : new String[]{\"sh\", \"-c\", \"echo \" + (a + b)});\n    Scanner out = new Scanner(p.getInputStream());\n    if (out.hasNextLine()) System.out.print(out.nextLine().trim());\n  }\n}",
    },
]


def build_grading_samples() -> dict:
    fill_blank = []
    for item_id, prompt, answer, nodes, explanation, wrong_answer in FILL_BLANK_QUESTIONS:
        submissions = [
            {"id": f"{item_id}-A", "answer": answer, "expected_status": "accepted", "label": "correct"},
            {"id": f"{item_id}-B", "answer": wrong_answer, "expected_status": "wrong_answer", "label": "wrong"},
        ]
        for edge in FILL_BLANK_EDGE_SUBMISSIONS.get(item_id, []):
            submissions.append(
                {
                    "id": f"{item_id}-{edge['suffix']}",
                    "answer": edge["answer"],
                    "expected_status": edge["expected_status"],
                    "label": edge["label"],
                }
            )
        fill_blank.append(
            {
                "id": item_id,
                "question_type": "fill_blank",
                "title": prompt.replace("____", "填空"),
                "prompt": prompt,
                "answer": answer,
                "explanation": explanation,
                "expected_nodes": nodes,
                "submissions": submissions,
            }
        )

    programming = []
    for item in PROGRAMMING_QUESTIONS:
        programming.append(
            {
                "id": item["id"],
                "question_type": "programming",
                "title": item["title"],
                "prompt": item["prompt"],
                "answer": None,
                "explanation": "编程题通过测试用例与大模型辅助评审综合判定。",
                "expected_nodes": item["expected_nodes"],
                "language": "java",
                "grading_mode": "testcase",
                "enable_testcases": True,
                "ai_review_level": "light",
                "ai_grading_rubric": "程序应满足题目输入输出要求，正确处理样例和边界情况。",
                "test_cases": [
                    {"input_data": case["input"], "expected_output": case["output"], "is_sample": True, "sort_order": idx}
                    for idx, case in enumerate(item["test_cases"])
                ],
                "submissions": [
                    {"id": f"{item['id']}-A", "code": item["correct_code"], "expected_status": "accepted", "label": "correct"},
                    {"id": f"{item['id']}-B", "code": item["wrong_code"], "expected_status": "wrong_answer", "label": "wrong"},
                ],
            }
        )
    for item in PROGRAMMING_EDGE_QUESTIONS:
        programming.append(
            {
                "id": item["id"],
                "question_type": "programming",
                "title": item["title"],
                "prompt": item["prompt"],
                "answer": None,
                "explanation": "边界编程题用于检验样例覆盖不足时的判题鲁棒性。",
                "expected_nodes": item["expected_nodes"],
                "language": "java",
                "grading_mode": "testcase",
                "enable_testcases": True,
                "ai_review_level": "deep",
                "ai_grading_rubric": "程序应满足题目完整语义要求，不能只通过当前样例。测试用例通过后仍需复核代码是否存在硬编码样例、只处理固定输入规模、违反指定算法、忽略题干边界、危险 API 或依赖外部环境等隐藏问题；发现上述问题应判为不通过。",
                "ai_grading_focus_json": [
                    "是否硬编码样例输入或样例输出",
                    "是否只处理固定输入规模而非题干要求的通用输入",
                    "是否违反题目指定算法或实现约束",
                    "是否忽略题干明确要求的边界条件",
                    "是否使用危险 API、外部命令或依赖运行环境副作用",
                ],
                "test_cases": [
                    {"input_data": case["input"], "expected_output": case["output"], "is_sample": True, "sort_order": idx}
                    for idx, case in enumerate(item["test_cases"])
                ],
                "submissions": [
                    {"id": f"{item['id']}-B", "code": item["wrong_code"], "expected_status": "wrong_answer", "label": "edge_wrong"},
                ],
            }
        )
    return {"fill_blank": fill_blank, "programming": programming}


def main() -> None:
    payload = {
        "version": "2026-05-27",
        "purpose": "Chapter 5 method-effectiveness experiments for RAG retrieval and assignment grading.",
        "reference_sources": [
            {
                "name": "Oracle Java Tutorials",
                "url": "https://docs.oracle.com/javase/tutorial/java/concepts/index.html",
                "usage": "Topic coverage reference for OOP, inheritance, interfaces, and classes; questions are original.",
            },
            {
                "name": "W3Schools Java Exercises",
                "url": "https://www.w3schools.com/java/exercise.asp",
                "usage": "Exercise style and coverage reference for syntax, arrays, loops, methods, collections, and exceptions; questions are original.",
            },
            {
                "name": "GeeksforGeeks Java Exercises",
                "url": "https://www.geeksforgeeks.org/java/java-exercises/",
                "usage": "Programming exercise topic reference for arrays, strings, loops, and basic algorithms; questions are original.",
            },
        ],
        "rag_retrieval": RAG_SAMPLES,
        "grading": build_grading_samples(),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
